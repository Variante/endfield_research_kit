# Data page (export stores and decoded datasets)

## Purpose

The Data page (`data-inspector`, after Assets in normal navigation) shows every
decodable export output that no other page shows. **Files** is one list and one
viewer over five sources: the export's Unity object documents
(`game/Unity.sqlite`), its packed game files (`game/GameFiles.sqlite`), the
loose decoded files under `game/` (tables, JsonData outside the packed folders,
Lua, Terrain, and converted Shader, Font and TextAsset), the undecoded files
under `raw/` (Streaming, DynamicStreaming, IV, ExtendData, IFixPatch, the bundle
manifest; always a hex dump), and the generated decoded datasets. **SQL** is a
read-only console over either SQLite store; the file sources have none.

Media the Assets and Audio pages show (videos, Texture2D, Sprite, Mesh, Animator
FBX, decoded audio) are left out on both sides: `scripts/webui/pages.py`
`PAGE_MEDIA` keeps them out of the page's extraction and
`store_browser.PAGE_MEDIA_FOLDERS` out of its list, and a local test keeps the
two equal. Sprite crop documents are Unity store rows, so the Data page lists
them while Assets shows the images. Assets lists no exported JSON: every such
document is a store row here.

## Inputs and recovery flow

1. `export.bat data --from-game` extracts the page's own inputs and everything
   it serves as files: Table, JsonData, Lua, whole Terrain, the undecoded
   blocks, every Unity JSON class, and the AnimationClip, Shader, Font and
   TextAsset conversions.
2. The store and file sources are read live through `serve.py`'s read-only
   `/api/stores` endpoints
   ([`store_browser.py`](../../scripts/webui/data_inspector/store_browser.py)):
   sources and group counts, a filtered page of rows across any set of groups,
   or one bounded SQL statement with `inflate(data)` and `doc(data, '$.path')`.
   Connections are read-only with an authorizer refusing writes and ATTACH.
   Documents are fetched from the URLs `serve.py` already answers, so the
   viewer shows exact exported bytes: JSON as a lazy tree with base64 decoded
   inline, text as text, anything else as hex. The loose-file list is indexed
   once per export (the layout marker, or a minute, invalidates it).
3. `python -m scripts.webui.data_inspector.build_data_inspector` publishes the
   decoded datasets. Each adapter calls the owning maintained
   `scripts/game_data` reader; families with a reader publish the reader's own
   result (`payloadKind: reader`), while already-decoded Unity JSON
   (AnimatorController, AnimatorOverrideController) publishes selected facts
   plus a mounted source link (`payloadKind: projection`) and the browser loads
   a bounded raw preview on request.
4. The frontend (`src/features/data_inspector/stores.js` for the shell and
   modes, `index.js` for decoded records) merges all sources into one paged
   sequence (Unity, packed, loose, undecoded, decoded). Sources and their
   groups are multi-select `WebUI.facets` chips; nothing selected lists every
   source, and a selected group narrows its own source. Decode status, source
   folder and tag filters appear only while decoded data is selected.

A static package has no store API: Files then lists only the decoded datasets
with an explanation, and SQL explains that it needs `python serve.py`.

### Decoded datasets

| Dataset | Owning reader / source | Published |
| --- | --- | --- |
| `animation-config` | `frame_animation_config` | complete reader result |
| `npc-montage` | `frame_npc_montage` | complete reader result |
| `animator-controller`, `animator-override-controller` | AnimeStudio JSON in the Unity store | selected projection plus raw source link |
| `level-config` | `decode_level_config` | complete reader result |
| `level-data` | `frame_leveldata_named_prefix` | per-file exact or bounded status with its open-field boundary and stored spline rows |
| `levelscript-data` | `frame_levelscript_named` | exact/bounded owner frames, byte ranges, opaque remainders and refused-profile diagnostics; native drift makes the dataset unavailable |
| `levelscript-template-data` | `frame_levelscript_template` | named template fields where closed, otherwise exact endpoint ranges and an explicit opaque middle; native drift makes the dataset unavailable |
| `spawner-config` | `frame_spawner_named` | named sequential enemy library, routes, settings and waves; refusals retain the earlier prefix and open range |
| `atmospheric-npc` | `frame_atmospheric_npc_table` | named proxy rows, or the reader's framed/opaque status; authored placements only |
| `map-config` | `schemas.map_config.decode_map_config` | all validated JSON fields, typed condition trees, scene-state indices and inverse variable dictionaries |
| `dynamic-components` | `dynamic_scalar_components_native.decode_authenticated_main`, `dynamic_root_comp_native.decode_authenticated_root_components` | native-authenticated component values, authored mission string references and direct authored root associations from existing raw main files; whole owners remain partial |
| `skill-data` | selected-native generated-wrapper values | `structural_only` records after EOF and filename-id checks; stored `AllowNextSkillAction` references and direct-action inventories |
| `buff-data` | canonical Buff family admission and original root reader receipts | complete named roots as unchanged reader payloads; every unresolved source remains a framing projection |
| `buff-action-receipts` | current report-backed spans for eight reviewed action wrappers | optional `bounded_partial` span projections |
| `char-interact-perform` | `decode_char_interact_complete_frame` | complete frame, else a bounded prefix row |
| `navmesh` | `decode_luna_area`, `decode_navmesh_state_container` | framed to EOF; unrouted names stay `unsupported` |
| `level-mount-point` | `decode_level_mount_points` | validated trees |
| `config-table` | one exact reader per single-instance table | reader result per table |

Per-dataset detail, including the SkillData inventory rules and the teleport
validation table's plaintext container, is in the
[`build_data_inspector`](../../scripts/webui/data_inspector/build_data_inspector.py)
docstring; the Buff receipt publication checks are in
[`buff_action_receipts`](../../scripts/webui/data_inspector/buff_action_receipts.py).

Publisher rules:

- The size badge says `cursor at EOF` when the reader cursor reaches the source
  length. Opaque prefixes or nested fields can remain; the badge never promotes
  a partial record to a complete named schema.

- A family is published only when a maintained `scripts/game_data` reader owns
  it. The adapter never softens that reader: status is the reader's own
  `schemaStatus`/`status`, a fail-closed variant becomes a visible
  `decode_error` row with its reason, and an unrouted file is `unsupported`,
  never omitted. A second container always gets its own reader, never a
  widened one.
- LevelScript publishes only while the selected installed native pair matches
  the reviewed union-tag contract. The selected hashes and gate status enter
  the dataset signature before cache reuse, together with the current reader,
  codec, layout and LevelScript contract bytes, plus the transitive local
  imports and declared resources of the reader. Shared formatter helpers must
  invalidate this page cache too; this cache signature alone never admits a
  saved schema receipt. Recovery edits therefore
  invalidate decoded shards even when the export and installed native pair are
  unchanged. Missing or mismatched inputs publish an unavailable dataset with
  no records. Whole-reader refusals remain visible
  `decode_error` rows with their structured source-hash diagnostics.
  A complete current canonical receipt may supply the same reader payloads
  without repeating the decode. Reuse requires the complete reader-input
  snapshot, selected native/source receipt, and a one-to-one path/length/hash
  join for the family, including drift checks around publication. A missing or
  stale receipt falls back to the maintained reader, bypassing old page caches.
  LevelScript owners and templates also authenticate the selected adjacent
  `UnityPlayer.dll` against the reachable child reader's reviewed native pins
  before reuse and after reading. The structured current guard is recorded in
  Data provenance. The canonical source receipt records GameAssembly and
  metadata explicitly; its complete reader/contract snapshot plus successful
  child admission establishes the required pinned Unity input through those
  loaders' checks. That implication is not a separately observed historical
  Unity receipt, and Data never fabricates one.
- SpawnerConfig and AtmosphericNpcData use the same reviewed union-tag input
  gate before cache reuse. Missing or mismatched native inputs publish no rows.
  SpawnerConfig reaches whole-file status only through its sequential wave
  cursor; a uniquely matched suffix cannot close an unknown earlier field.
  Atmospheric NPC EOF framing can still contain opaque nested bodies.
- SkillData publishes only while the selected native plan validates; missing or
  mismatched inputs publish an unavailable dataset with a diagnostic, and the
  source signature includes the native hashes, so old shards are never reused
  across a client change.
  Optional `facts.canonicalRootEvidence` separately exposes source-matched
  canonical framing. Its receipt authenticates the complete family report,
  current parser and contract closure, selected native inputs, and every
  source. The bounded report-header reader avoids materializing its large
  file array; complete-file hash checks still guard the report. Complete EOF
  framing and recursively named fields are different claims: the detail view
  states both, while the derived values retain `structural_only`. A stale or
  missing canonical receipt suppresses the extra facts and forces a current
  derived decode; it does not promote old cached values.
- DynamicStreaming components require the selected native layouts, authenticated
  current VFS roster and a byte join for every existing raw main file before
  cache reuse. Field values, grid and component ordinals stay verbatim. Mission
  string references retain their stored index, including zero. A separately
  validated native root route and fresh template asset supply direct authored
  root associations by the same grid, component vector and stored element
  index. Refused template/root evidence retains scalar fields with an explicit
  ownership diagnostic; group children are not assigned indirectly. Live string
  keys, condition evaluation and runtime entity ownership are unresolved. Large integers use
  the publisher's existing exact-string representation.
- Buff action spans use the reviewed catalog's short or extended union header.
  Strictly contained spans are permitted; duplicates and crossing spans refuse
  publication. Containment does not establish action hierarchy or close the
  enclosing Buff schema. The census and action report must authenticate each
  other and the selected native inputs. The shared domain helper replays every
  selected codec against the physical source bytes and independently certified
  child spans; names, kinds, ranges and structural fields must match. Each route
  retains its own declared native input set.
- Buff roots follow the current canonical registry's family-report pin. Before
  cache reuse, the adapter authenticates that registry, the full family report,
  its reader and native input closure, and every exported logical source by
  path, length and digest. A complete row passes through its original root
  receipt, including all named fields and physical EOF; an unresolved source
  stays visible without an invented partial root. Missing or stale evidence
  makes the dataset unavailable.
- WebUI code never duplicates binary framing. A family without a reader gets a
  reader and corpus gate in `scripts/game_data/` first.
- Dictionary keys remain verbatim in the field tree, preview and search,
  including numeric IDs and decimal UInt64 keys. Only actual array indices
  receive one-based ordinal labels.
- Increment `PUBLISHER_REVISION` whenever a projection or normalization
  changes; cache reuse requires it and the source signature.

## Primary generated outputs

`webui/data/data_inspector/index.json` and
`webui/data/data_inspector/datasets/<id>/{index,records.NNNN}.json`. The
envelope, record fields, id rules, and strict browser-safe JSON (large integers
as decimal strings, non-finite floats as strings) are owned by
[`contract.py`](../../scripts/webui/data_inspector/contract.py);
`publish_dataset` fails closed on a payload without a valid `payloadKind`. The
catalog carries only what search and selection need; domain data stays in the
lazy shard. Inspector data is local recovery output, excluded from the
published WebUI archives.

## Evidence boundary

- The page promotes nothing. A decoder's `schemaStatus`, `status`, ranges,
  diagnostics and `evidenceBoundary` pass through unchanged; unknown, partial
  and failed rows stay visible.
- The viewer is taught no decoder-specific schema. Read order, declared but
  undecoded members, framing metadata, byte ranges, PPtr references and
  boundaries are recognized by shape alone, and field names are shown verbatim
  in every locale so rows stay searchable against the export, the contract and
  the reader. The detailed viewer rules are in the header comment of
  `webui/src/features/data_inspector/index.js`.
- `facts` is the publisher's projection and `payload` is labelled by
  `payloadKind`. Only a `reader` payload receives framing chips; a publisher
  `evidenceBoundary` is shown as a publisher claim, never a decoder claim, and a
  publisher must not report a framing status it did not establish.
- Controller summaries are a convenience projection; the mounted raw file is
  the exact source. PathID "find" in the store viewer is an index lookup, not a
  resolved reference.
- LevelScript exact status closes only the stored reader profile at physical
  EOF; partial maps and uniquely matched suffixes keep the reader's bounded
  status and opaque ranges. Neither establishes execution or mission ownership.
  Reviewed registrations, typed parent contexts and adapter/interface ABI joins
  establish the default stored grammar for positive camera pose lists and the
  squad-USP header. They do not establish live provider replacement, cache
  selection or evaluated values. Unreviewed child routes retain their explicit
  field, cursor and refusal diagnostic.
  Templates preserve the same reader boundary: a uniquely framed terminal
  `templateId` does not make an opaque action/task-map middle named or exact.
  Their pre-cache gate includes the selected `UnityPlayer.dll` required by
  reachable child readers, as well as GameAssembly, metadata and the complete
  current reader dependency snapshot.
  `GetClientMapVar` preserves the authored key and stored `mapId` parameter;
  an anonymous source selector does not establish the selected map or live
  variable value. `GetSquadInFight` preserves the stored getter identity and
  inherited fields, without an evaluated combat-state result.
- SkillData references, search terms and occurrence lists are authored storage
  in stored array order; they establish no runtime transition, execution order
  or timing. Buff action receipts locate verified wrapper spans only; complete
  Buff root receipts establish stored fields, not evaluated effects or ownership.
- Search tags, filenames and character-like tokens are navigation aids, not
  ownership.
- Spawner actions, NPC positions and MapConfig predicates are authored storage.
  Browsing them establishes no spawning, execution, currently visible scene or
  evaluated condition. MapConfig preserves every validated field and refuses
  duplicate keys rather than silently accepting the last occurrence.

## Focused refresh commands

```bat
python -m scripts.webui.data_inspector.build_data_inspector
python -m scripts.webui.data_inspector.build_data_inspector --dataset levelscript-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset levelscript-template-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset spawner-config --dataset atmospheric-npc --dataset map-config
python -m scripts.webui.data_inspector.build_data_inspector --dataset skill-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset buff-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset buff-action-receipts
python -m scripts.webui.data_inspector.build_data_inspector --force
```

The export freshness check covers only what the dataset builder reads (JsonData,
DynamicStreaming, animator controllers and the MonoBehaviour template asset);
served files are shown as exported. Buff receipts select the current census
from the authenticated JsonData registry's family-report pin by default,
preserving historical census paths used by saved receipts. The action report
must match that census (`--buff-corpus-report` explicitly overrides selection;
`--buff-action-receipts-report` selects the matching inventory). Source/catalog
provenance is rechecked before and after following the census pin. The build cache is keyed on the input
signature and publisher revision and is not game-data evidence; `--force`
bypasses it.

## Highest-value remaining gaps

Candidate families for a publisher adapter (reader boundaries are owned by
[`../game_data/extraction_payload_boundaries.md`](../game_data/extraction_payload_boundaries.md);
file counts belong in `reports/animestudio/`):

| Candidate | Owning reader | Why it is worth publishing |
| --- | --- | --- |
| Remaining Buff interiors | `memorypack.buff*` | the root dataset exposes admitted complete readers and explicit unresolved sources; additional partial interiors need reusable reader receipts before publication |
| Interactive, UILevelMapLoadConfig, GPUISystemConfig, MissionRuntimeAsset | their `scripts/game_data/*_binary.py` / `*_json.py` readers | mid-size families with maintained readers and no page of their own |
| LipSync | `memorypack.lipsync` | an exact 15-member reader through EOF, but the largest JsonData family; it needs a paged catalog first |
| StringPathHash, FacBoneTRS | `extend_data_binary` | the global source-path catalog and facial-bone data; self-bounded, and useful for resolving path hashes seen in other records |
| Unity MonoBehaviour, PlayableDirector, TextAsset | already-decoded AnimeStudio JSON | the projection-plus-source-link shape the controller adapters use; MonoBehaviour is the largest Unity family |

Not candidates: Terrain, Streaming/DynamicStreaming, irradiance volumes and
BundleManifest decode to anonymous ranges with no per-record identity; Audio,
Story/Text, Map and Gameplay data belong to their own pages.

Canonical registry entries are not automatically reusable reader payloads.
The Interactive branches retain recovery summaries, and the shared
`jsondata_corpus._run_reader` projection also omits template field values.
The template dataset therefore calls its small maintained reader directly.
An Interactive receipt adapter would first need canonical publication to
retain the owning reader's full result, then authenticate its current reader,
native and source inputs. Summary-only rows cannot supply decoded values.

- Publish a family's own reader boundary; never promote a partial frame to a
  complete one, and keep the frontend envelope unchanged.
- A family too large for one searchable catalog needs a versioned paged-catalog
  schema, not silent truncation.
- Add Characters deep links only after a decoder exposes an exact or explicitly
  typed character identity; filename resemblance is insufficient.
