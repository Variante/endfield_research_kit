# Endfield game-data recovery

This is the single durable memory source of truth for recovering, decoding, and
interpreting Endfield game data outside the static WebUI workflow, Story
reconstruction, and character rendering/animation work.

Those neighboring scopes live in:

- `memory/webui_recovery.md`
- `memory/game_story_recovery.md`
- `memory/asset_recovery.md`
- `memory/animestudio_recovery.md`
- `memory/character_render_and_animation_recovery.md`

Detailed generated inventories belong under `reports/`; disposable probes and
reproduction output belong under `scratch/` or `tmp/`. This note keeps current
conclusions, evidence boundaries, commands, and the remaining recovery queue.

## Current conclusion

Basic access to the installed data is solved. The active exporter can index the
StreamingAssets and Persistent VFS roots without missing chunks, dump the
WebUI-relevant table and config blocks, and recover more than a million Unity
JSON objects without generic unparsed fallbacks. The hard work is now semantic:
proving binary field layouts, connecting authored records across systems, and
distinguishing static config values from live runtime behavior.

The current checkout has three complementary evidence layers:

1. Structured tables and text JSON provide the strongest authored field and
   relationship evidence.
2. Family-specific MemoryPack, FlatBuffer, and MonoBehaviour decoders expose
   binary configuration that is not regular JSON.
3. `tools/endfield_source_graph.py` joins those records, IL2CPP metadata, Lua
   consumers, decoded audio, and selected exported assets into an evidence-first
   SQLite graph.

The graph is broad enough for practical gameplay, progression, economy,
factory, world, audio, and configuration research. It is not a runtime
simulator. Values and edges prove what the client authors or references; they
do not by themselves prove evaluator order, server state, account state,
physics, AI decisions, or final combat formulas.

## Active evidence and refresh path

Use the root wrappers for normal refreshes. They load the configured local paths
from `endfield_paths.bat`.

```bat
.\export.bat
.\export.bat --export-from-game
.\export.bat --export-from-game --with-assets
python scripts\verify_export_freshness.py
```

`export.bat` reuses `export_full/` by default and verifies its fingerprints
before builders consume it. Use `--export-from-game` only when an installed-game
refresh is intended. The combined `--with-assets` path is appropriate only when
Story and asset outputs both need the installed data refreshed; asset/rendering
details are owned by the separate recovery note.

After an installed-game refresh, use these as current evidence rather than
copying their counts into new memory snapshots:

- `reports/export_full_summary.md`
- `reports/source_graph/summary.md` and `summary.json`
- `reports/monobehaviour_frontier_latest.md` and `.json`
- `export_full/unresolved/failed_to_decode.txt`
- `export_full/unresolved/manifest_reference_missing.txt`

The 2026-07-09 export summary reports:

- StreamingAssets: 258,422 VFS files in 32 chunks, 0 missing chunks.
- Persistent: 261,685 VFS files in 33 chunks, 0 missing chunks.
- Structured `table`, `json-data`, `video`, and `audit-video` stages returned
  zero actual failures for both roots.
- AnimeStudio map and JSON-by-type jobs succeeded for both roots.
- `failed_to_decode.txt`: 0 entries.
- `manifest_reference_missing.txt`: 0 entries.

These are extraction-health claims, not a certificate that every decoded field
has the correct runtime meaning.

## Installed-data and VFS model

The installed client has two source roots with the same logical VFS shape:

- `Endfield_Data/StreamingAssets` is the primary source.
- `Endfield_Data/Persistent` is the fallback/patch source.

VFS-aware commands must accept `--fallback-assets`; inspecting only the primary
root can miss patched content. AnimeStudio's integrated `dump`, `audio`,
`stream`, and `vfs-index` commands are the maintained path. A focused 2026-07-03
parity check against the local Rust Fluffy Dumper build found identical parsed
metadata for the `table` and `json-data` blocks, excluding only the generated
timestamp:

| Block | Chunks | Files | Bytes |
| --- | ---: | ---: | ---: |
| `table` | 42 | 629 | 161,084,549 |
| `json-data` | 69 | 81,735 | 700,046,680 |

The lean WebUI structured mode deliberately skips raw bundles, Wwise packages,
world-streaming bytes, irradiance volumes, ExtendData, patch bytes, and Lua.
Skipped means outside that export plan, not missing. The saved skipped-block
audits reported zero missing blocks and zero missing chunks and remain useful
for selecting future recovery targets.

Important raw families are:

- `.ab`: Unity asset-bundle payloads and their maps;
- `.pck` / Wwise media: bank metadata and packed audio;
- `.bytes`: mostly world-streaming FlatBuffer-like data;
- `IrradianceVolume`, `DynamicStreaming`, and `ExtendData`: schema-specific
  binary data outside ordinary table/config decoding;
- Lua: useful consumer-side evidence for table names and gameplay/UI usage.

Do not infer that a VFS block is irrelevant merely because the normal WebUI
export skips it. Promote it only when a bounded decoder or query need justifies
the cost.

## Structured tables and decoded config

The strongest static gameplay evidence comes from
`export_full/structured/StreamingAssets/Table/*.json` plus parseable text config
under `Data/Json`. Structured table rows retain authored names, localized-text
ids, foreign keys, lists, and numeric constants. The source graph turns many of
those relationships into typed forward and reverse edges.

The `Data/Json` extension is misleading. A prior full census across
StreamingAssets and Persistent found about 164,000 config files, only about
6,000 of which were ordinary parseable JSON. Most are binary MemoryPack-like
payloads carrying a `.json` name. Browser or script code must classify the
payload before using a JSON parser.

The maintained decoder policy is fail-closed:

- accept exact layouts only when member counts, field widths, bounds, enums,
  booleans, strings, and final offsets validate;
- expose bounded prefixes, tails, string hints, RID links, and raw words when a
  nested body remains uncertain;
- preserve an explicit partial/diagnostic state instead of silently skipping a
  field or inventing a label;
- treat StreamingAssets and Persistent copies independently when patch deltas
  matter.

### MemoryPack dialect

The current binary-config work established these reusable rules:

- Object: one-byte member-count header, or `0xFF` for null.
- List: little-endian `u32` count, or `0xFFFFFFFF` for null.
- String: little-endian `u32` byte length followed by strict UTF-8, or
  `0xFFFFFFFF` for null.
- Serialized member order is base-class members first, then each class level in
  ordinal alphabetical member-name order. IL2CPP field-token order is not the
  serialization order.
- Polymorphic/union members use a null marker or tag followed by the subtype
  object and its own member-count header.
- Generated MemoryPack wrappers and GameAssembly deserializer setter order are
  stronger schema evidence than field declaration order alone.

These rules enabled exact recovery of `SelectorData`, `TargetSettings`,
`DirectionSettings`, `FindTargetAction`, and `ContinuousFindTargetAction` in
the BuffData corpus. Every current FindTarget occurrence decodes exactly; the
remaining ambiguous BuffData chains are blocked by other action families, not
selectors. Two selector subtype payloads remain intentionally unsupported
until samples exist: `ShapeFinder+Data` and `PriorityFilter+Data`.

### Family status

The following table summarizes durable status without reproducing every old
per-session count.

| Family | Current recovery status |
| --- | --- |
| `DialogIdTable`, `ModelTable`, `ModelRadiusTable`, `InteractiveTable`, `WorldEntityRegistry` | Exact or exact for their maintained top-level/index layouts. |
| `NavMesh/*/LunaArea` and `NavMeshStateContainer` | Exact for the observed current variants. |
| Selected mission-area, teleport, non-generated table, and compact lookup roots | Exact family-specific readers where maintained. |
| `LevelConfig` | Verified ids, default-state data, path counts, map ids, and numeric transform/bounds tails; middle path/grid body remains bounded. |
| `LevelData` | Parent scene ids and useful references are verified; much of the 42-member body remains partial. |
| `LevelScriptData` | Large action/condition surface has typed readers, but unknown action families and some chain boundaries remain. Story ordering conclusions belong in the Story note. |
| `BuffData` | Top-level schema, large prefix/tail regions, stacking data, action chains, and SelectorData are substantially recovered; 48 ambiguous chains per root remain in non-selector action families. |
| `SkillData` | Verified id and post-id fields plus the default switch-to-buff branch; action groups and non-default nested bodies remain partial. |
| `SpawnerConfig` | Exact id and enemy-library rows; waves, routes, and settings remain partial. |
| `AnimationConfig`, NPC montage, character-interact config, atmospheric NPC config | Useful verified summaries and references exist; visual/animation interpretation belongs to the render recovery scope. |
| `InteractiveTemplateData` and related interactive component blobs | Several component maps and compact bodies are exact; complex click/trigger/ability/dynamic-nav records remain bounded stop points. |
| World-streaming `.bytes` | FlatBuffer root families and selected structural joins are proven; most field names and nested scalar/struct vectors remain unresolved. |

## World-streaming FlatBuffers

A 2026-07-01/02 census found 38,824 `.bytes` files under StreamingAssets;
38,561 passed strict FlatBuffer root checks. The 263 rejects were custom
IrradianceVolume payloads, not arbitrary parse failures. Valid files clustered
into five root vtable signatures, dominated by 38,064 InitChunkData,
StreamingChunkData, and related chunk-manifest files.

Two population-scale facts are strong:

- root slot 0 is the constant `46` for all 38,064 dominant-family files;
- for 36,554 coordinate-named chunk files, the inline pair at root slot 1 is
  exactly the filename coordinates multiplied by 128, with zero mismatches.

The dominant root also contains vectors of named object records. Samples expose
collider, merged-renderable, lighting, audio-placement, terrain, surface, and
interactive/prefab names. Static and dynamic chunk files share the same root
shape. Negative sampling found no `dlg_*`, `eny_*`, `chr_*`, `npc_*`, or
`sc_*` identifiers, so this population should be treated as scene
geometry/lighting/audio streaming rather than a source for Story order.

Do not revive the original permissive slot classifier. The corrected probe
distinguishes proven table/string vectors from unknown scalar/struct vectors.
Before promoting a typed reader, recover accessor names from IL2CPP or other
writer-side evidence and tighten all object-width checks. Empty string versus
empty vector and scalar versus forward offset remain inherently ambiguous
without schema evidence.

## MonoBehaviour and runtime payload recovery

AnimeStudio uses serialized type trees first by default. Optional DummyDlls add
script-schema evidence but must never make a normal export fail when absent or
stale. `script-first` is for targeted experiments only.

Managed-reference recovery now combines:

- Unity serialized type-tree structure;
- generated DummyDll/script metadata when usable;
- IL2CPP metadata fields, methods, types, and MemoryPack wrappers;
- RID-to-managed-object links;
- byte-bounded, type-specific readers;
- conservative raw-word and aligned-string diagnostics as a final fallback.

A fresh 2026-07-03 MonoBehaviour index, which superseded the stale WebUI
decoded index, measured:

- 1,064,294 JSON files;
- 1,063,560 decoded;
- 734 partial;
- 0 unparsed;
- 21 residual groups.

The leading residuals were concentrated rather than broad: 310 projectile
templates across both roots, 161 ability-entity templates, 156 enemy templates
across both roots, 48 LineFollower records, and 28 character templates. Some
substructures have improved since that census, so regenerate the frontier
before using those numbers as a current task ranking.

### Proven gameplay payload advances

- Focused character `AbilitySystemData` rows consume the validated parent
  structure through skill bundles, command mappings, combo conditions, UI
  data, buff lists, entity blackboards, skill-camera configuration,
  post-camera fields, preload ability entities, and potential buff ids.
- `AbilityEntityRootComponentData` is exact for the observed current layout;
  the enclosing `AbilityEntityTemplateData` remains partial.
- Physics and observed NavMesh-obstacle component shapes have guarded readers.
- `EffectActionCfg` now has exact guarded readers for the observed dead-effect,
  projectile alert-effect, and projectile effect-list variants. The two
  observed layouts are not interchangeable.
- Projectile component recovery covers the stable prefix, move-mode maps,
  Bezier records, effect lists, alert effect, sound tail, and final suffix for
  validated samples. The enclosing projectile template remains a frontier.
- `SelectorData` and FindTarget actions are byte-proven in MemoryPack BuffData;
  the result does not automatically transfer to Unity TypeTree serialization.
- Simple InteractiveEvent actions such as add/remove tag, animation, sound,
  skill cast/attach, and exit-throw-mode have narrow readers. Complex attach,
  enter-throw, and component records remain partial diagnostics.
- LineFollower records have a stable row structure with named control fields;
  the nested line value remains raw.

An incomplete marker is evidence about semantic coverage, not necessarily an
export failure. Keep partial payloads queryable, connect their proven ids to the
source graph, and avoid warning-count work that merely hides unresolved bytes.

## Source graph

`tools/endfield_source_graph.py` builds the local evidence database. The project
skill `.codex/skills/endfield-source-graph/` is the current operational guide;
this section records the durable model and boundaries.

Quick and full builds:

```bat
python tools\endfield_source_graph.py build --skip-asset-maps
python tools\endfield_source_graph.py build
```

Useful cost controls:

- `--skip-gameplay`
- `--skip-asset-maps`
- `--skip-reference-rows`
- `--skip-followups`
- `--include-all-material-json`
- `--db PATH` for a disposable focused database

Core outputs under `reports/source_graph/` are:

- `endfield_source_graph.sqlite`
- `summary.json` and `summary.md`
- `voice_audio_links.json`
- `character_recovery_candidates.json`
- `option_branch_gaps.json`
- `map_level_index.json`
- `semantic_update_summary.json`

The 2026-07-15 full graph summary reports 5,345,967 nodes, 11,182,819 edges,
5,489,598 aliases, and 499,701 files. It includes 1,075 structured tables,
159,884 decoded game-data files, 724 Lua modules, and large asset/audio
indexes. These totals are build artifacts and should be read from the latest
summary after refresh.

Core SQLite tables are:

- `nodes(id, kind, name, source, path, data)`
- `edges(src, dst, kind, source, evidence, data)`
- `aliases(alias, node_id, kind, source)`
- `files(path, kind, source, size, data)`
- `meta(key, value)`

Edges should preserve evidence quality. Direct authored foreign keys,
byte-proven decoded fields, filename/path aliases, normalized identifiers, and
inferred bridges are different claims and must remain distinguishable in edge
kinds or edge data.

### Query surfaces

The generic commands remain useful:

```bat
python tools\endfield_source_graph.py query item_gold --kind item --limit 20
python tools\endfield_source_graph.py item-usage item_gold --limit 20
python tools\endfield_source_graph.py progression-usage chr_0004_pelica --limit 20
python tools\endfield_source_graph.py stat-usage atk --limit 20
python tools\endfield_source_graph.py formula-usage component_activity_xiranite_cmpt_1 --limit 20
python tools\endfield_source_graph.py factory-flow miner_2 --limit 20
python tools\endfield_source_graph.py blackboard-usage atk_scale --limit 20
python tools\endfield_source_graph.py map-usage map01 --limit 20
python tools\endfield_source_graph.py audio-usage action_dash_start --limit 20
```

Other maintained query families cover entity assets, shaders, materials,
effects, animations, videos, actors, text, mission flow, and Story issues. Their
domain conclusions belong in the render or Story notes when applicable.

### Gameplay domains represented

The graph has typed nodes and reverse links for these broad authored systems:

- characters, professions, elements, tags, teams, presets, tutorials, trials,
  level/breakthrough/potential progression, skills, talents, weapons, weapon
  upgrade/break/talent templates, and stat checkpoints;
- enemies, templates, attributes, abilities, buffs, global effects, use-item
  effects, blackboard keys, target selectors, damage-scalar tables, and
  gameplay tags;
- equipment, suits, formulas, gem terms/tags/presets/pools, enhancement,
  dismantling, items, obtain ways, rewards, shops, currencies, gacha, cash
  shops, check-ins, and battle passes;
- maps, levels, areas, marks, collectables, world entities, interactive
  templates, spawners, dungeons, training, world energy, harvestables, crops,
  domain depots, tower defense, and snapshot/Kite Station content;
- factory recipes, items, machines, craft groups, technology, manual craft,
  logistics, regions, blueprints, miners, power, fuel, batteries, liquids,
  fluid machines, and sewage treatment;
- activities, achievements, system jumps, game mechanics, guides/wiki, PRTS
  archive/reading content, profile/social catalogs, settings, and UI labels;
- NPC metadata, ambient/responsive bark configuration, Wwise banks/events/media,
  audio dialog/config records, decoded config references, IL2CPP focus metadata,
  and Lua-to-table consumer references.

This breadth replaces the old pattern of one memory file per table or reverse
edge. Add maintained ingesters and query support when a relationship is
reusable; keep one-off validation output in `tmp/` and generated summaries in
`reports/`.

## Current semantic understanding

### Progression, economy, and catalog data

Authored progression is strong enough to answer static questions about level
costs, breakthrough requirements, potential unlocks, weapon checkpoints,
equipment formulas/suits, gem pools, item acquisition, rewards, shops, gacha,
activities, battle passes, and dungeon/training catalogs.

Weapon upgrade tables expose 3,780 normal and cumulative checkpoints; 1,890
normal checkpoints carry authored `baseAtk` evidence linked to the `atk` stat.
Character and equipment checkpoints similarly expose authored values and costs.
These links do not prove the runtime getter path, modifier order, live inventory
rolls, or account progression.

### Factory and world systems

Factory relationships are well represented at the static-config layer:
machines consume recipes and items, technology unlocks capabilities, logistics
and blueprints link to buildings, and utility tables expose authored power,
fuel, battery, liquid, mining, and sewage constants.

The numerical utility slice establishes interpretable constants such as
`msPerRound`, `msTransferCD`, fuel energy/power/progress rounds, battery energy,
power-pole ranges, liquid bottle conversions, machine capacities, and sewage
upgrade actions. It does not prove the live power-grid solver, network transfer
scheduling, throughput equation, placement validation, or world/account state.

WorldEntityRegistry and related decoded config provide thousands of static
placed instances and links to models, interactives, enemies, audio collections,
and level-script slots. That is sufficient for authored placement queries, not
a full reconstructed runtime world or scene simulation.

### Combat, abilities, and numeric fields

The project can recover many authored combat values and named payload fields,
but the final formula boundary remains important.

Examples of strong static evidence include:

- five authored all-damage-taken levels from 0.0 to 1.0;
- 113 enemy attribute templates with physical, fire, pulse, crystal, and
  natural damage scalar fields;
- character, weapon, equipment, and enemy stat checkpoints;
- buff parameters, blackboard keys, target selectors, effect actions, and
  ability-entity components linked through decoded config and metadata.

Display formatting and normalized graph stat names can differ from raw source
field names. For example, raw `*DmgResistScalar` values are linked to normalized
damage-taken stat keys, while some display config formats `1 - value`. Preserve
the raw authored field and value alongside the normalized semantic alias.

No static table or graph traversal proves where defense, resistance,
vulnerability, shields, resilience, conversion, buffs, and difficulty scalars
enter the live damage pipeline. Runtime consumer/evaluator evidence is required
before documenting a final equation.

### Audio, Lua, and consumer evidence

Wwise bank metadata now links events to media and decoded files, while table and
config ingesters link gameplay, factory, level, item, NPC, bark, and dialog
records to audio ids. This is strong ownership/reference evidence. It does not
recover every runtime RTPC, switch, state, mix, spatialization, or event
scheduling behavior.

The Lua audit promotes exact `Tables.*` consumer references and focus tags into
the graph. Lua references are valuable proof that a client module consumes a
table, but a name match alone does not prove the branch, timing, or server-side
conditions under which it is used.

## Evidence rules and known boundaries

Use this confidence order when adding a decoder or graph relation:

1. exact authored table/config foreign key or byte-exact decoded field;
2. generated wrapper plus matching GameAssembly deserializer behavior;
3. IL2CPP field/method/type metadata with a validated payload boundary;
4. direct path, filename, PathID, bank-event, or Lua consumer reference;
5. normalized identifier or repeated cross-source alias;
6. heuristic token/name similarity, which must stay labeled as inferred.

Keep these boundaries explicit:

- Static client config does not prove live server rotations, store
  availability, account progress, inventory, reward claims, or event state.
- Authored scalars do not prove runtime formula order or unit conversion.
- A successful decode does not prove a guessed field meaning.
- VFS completeness does not certify every asset bundle warning-free at the
  individual object level.
- StreamingAssets and Persistent often mirror one another, but patch deltas can
  exist and should be compared when relevant.
- Focused sample validation proves only the guarded shapes exercised by those
  samples; future variants must fall back visibly.
- Metadata type names and wrapper member lists are schema evidence, not byte
  boundaries, until replayed against real payloads.
- Graph aliases improve discovery but must not erase the distinction between
  direct and inferred relationships.

## Recovery queue

Prioritize work that improves reusable semantics rather than producing another
dated inventory snapshot:

1. Regenerate the MonoBehaviour frontier from the current export and finish the
   concentrated projectile, ability-entity, enemy, and character template
   tails with guarded readers.
2. Decode the remaining 48 ambiguous BuffData action chains per root, starting
   with repeated action families such as FinishBuffAdvanced,
   CheckBuffStackNumAdvanced, HitStopAction, and SpawnEnemyAction.
3. Trace one bounded combat formula from authored table/decoded payload through
   the actual runtime consumer and evaluator order. Keep display transforms and
   raw scalars separate.
4. Recover IL2CPP accessor names for the dominant world-streaming FlatBuffer
   root before promoting more field labels or scalar/struct vector decoders.
5. Expand direct reverse links only when they answer a maintained query. Prefer
   a new typed graph edge and smoke test over a standalone memory report.
6. Compare StreamingAssets and Persistent binary families when patch behavior
   matters, using hashes and schema-aware diffs rather than assuming mirrors.
7. Improve per-source/per-object warning attribution if an actual clean-export
   certificate becomes necessary; do not infer it from aggregate success.

When one of these changes lands, update this file's current conclusion and
queue. Put detailed counts in generated reports and remove obsolete session
notes instead of creating another distributed recovery memo.
