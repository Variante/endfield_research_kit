# Decoded page (鏁版嵁瑙ｇ爜: export stores and decoded datasets)

## Purpose

The Decoded page (`data-inspector`, after Assets in normal navigation) shows every
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
two equal. Sprite crop documents are Unity store rows, so the Decoded page lists
them while Assets shows the images. Assets lists no exported JSON: every such
document is a store row here.

World component publication uses the current selected native layout and each
authenticated VFS/raw byte join. Before returning rows it rechecks native,
UnityPlayer, VFS, raw-file and reader/contract inputs; drift withholds the
dataset. Optional authored-root associations keep their independent native gate
and remain unresolved when it refuses. Stored fields do not establish runtime
ownership, activation or condition execution.

## Inputs and recovery flow

LevelScript and Template publication uses one `complete_levelscript_reader`
operation over the independent selected source inventory. Native root, reached
child and actual parent-call proofs precede decoding. Every selected source
must close its ordered fields and physical EOF, and native, source, complete
reader and StringPool exit checks pass before either dataset publishes. A
partial legacy receipt or page cache cannot bypass this operation.

A full Data publication first requires every authenticated JsonData source to
be schema-decoded. The completeness guard reads and enumerates through the
game-file abstraction: packed LipSync rows and loose files share the same
logical roster and exact length/SHA checks. A packed logical path is not a
filesystem path; missing or extra store rows still refuse publication.

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

ModelView rebuilds its decoded records on every publication through one freshly
proved native operation. Its final source, StringPool, reader, publisher and
selected native/Unity checks withhold rows after drift; refused frames remain
explicit source records. The byte-coverage reader uses the same current graph,
and InteractiveData uses its own complete current source-backed operation.

### Decoded datasets

| Dataset | Owning reader / source | Published |
| --- | --- | --- |
| `model-view-state` | `model_view_state_controller_binary.model_view_operation` | complete current stored graph with native field names, model/layer/state owners and stored audio fields; no runtime or Event links |
| `animation-config` | `complete_animation_reader` | complete fifteen-field current graph, ExtraData/Montage children and both curve key layouts; all owners require physical EOF and a successful native/source/pool exit receipt |
| `npc-montage` | `frame_npc_montage` | complete named root and bounded positive Deco/Dynamic/extra-effect/transition lists; selected native/source/pool exit receipt in provenance; stored animation configuration only |
| `animator-controller`, `animator-override-controller` | AnimeStudio JSON in the Unity store | selected projection plus raw source link |
| `level-config` | `decode_level_config` | complete reader result |
| `level-data` | `complete_leveldata_reader` | authenticated current sources, all forty-three fields and physical EOF; incomplete roots or failed exit gates stop publication |
| `levelscript-data` | `complete_levelscript_reader` | authenticated current sources, all twenty-eight fields and physical EOF; incomplete roots or failed exit gates stop publication |
| `levelscript-template-data` | `complete_levelscript_reader` | independently proved six-field root and ActionMap/property/Task caller joins, complete stored values through physical EOF |
| `interactive-data` | `complete_interactive_reader` | complete named root, independently proved reached components, Params, collections and ActionMap nodes; every selected source requires physical EOF and successful exit gates |
| `spawner-config` | `frame_spawner_named` | named sequential enemy library, routes, settings and waves; refusals retain the earlier prefix and open range |
| `atmospheric-npc` | `frame_atmospheric_npc_table` | named proxy rows, or the reader's framed/opaque status; authored placements only |
| `map-config` | `schemas.map_config.decode_map_config` | all validated JSON fields, typed condition trees, scene-state indices and inverse variable dictionaries |
| `dynamic-components` | `dynamic_components_corpus.current_main_files`, `dynamic_root_comp_native.decode_authenticated_root_components` | complete current main roots and grid fields, all reached inline children and native zero padding; independently authenticated authored strings and root associations |
| `skill-data` | current native root and complete named stored values | `named_exact` after full source/native replay, ordered child/union and field-boundary checks; stored `AllowNextSkillAction` references and direct-action inventories |
| `buff-data` | canonical Buff family admission, original root receipts and native-owned value projection | all named stored values, raw numeric bits and independent root/child field extents; every root requires physical EOF |
| `buff-action-receipts` | current source-owned action spans, including concrete EffectActionData lists | named action values joined to independently replayed child spans; a span does not establish its enclosing Buff schema |
| `char-interact-perform` | `complete_perform_reader` | whole current stored graph, all twenty-eight root fields and physical EOF; failed roots stop publication |
| `navmesh` | `decode_luna_area`, `decode_navmesh_state_container` | framed to EOF; unrouted names stay `unsupported` |
| `level-mount-point` | `decode_level_mount_points` | validated trees |
| `config-table` | one exact reader per single-instance table | reader result per table |

Per-dataset detail, including the SkillData inventory rules and the teleport
validation table's plaintext container, is in the
[`build_data_inspector`](../../scripts/webui/data_inspector/build_data_inspector.py)
docstring; the Buff receipt publication checks are in
[`buff_action_receipts`](../../scripts/webui/data_inspector/buff_action_receipts.py).

Publisher rules:

- DynamicComponents rebuilds from the selected raw export and authenticated VFS
  roster. Every root needs all five root fields, all sixty-one grid fields,
  complete reached struct fields and physical byte closure. Native builder
  Prep/Put/Pad programs establish alignment and zero-fill; a zero residual alone
  never establishes padding. Nonempty descriptor tables require an independent
  positive grammar and otherwise stop publication. Native/Unity, VFS/CLI, raw
  sources, reader/contract inputs and authored-template provenance are checked
  through exit. A failed root or exit stops the dataset before page-cache reuse;
  earlier scalar projections cannot serve as complete roots. Template freshness
  uses the selected export's per-output extraction provenance, asset map,
  manifest and object store, without requiring an old summary or a report.

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
  Both LevelScript families rebuild through the complete current operation.
  The independent source inventory authenticates selected bytes and supplies no
  named grammar. Root and nested native proofs, selected adjacent UnityPlayer,
  every source hash, matching pool and complete raw-reader snapshot must remain
  current through exit. A refused record stops publication with its source and
  gate; it cannot become an available partial dataset.
- SpawnerConfig and AtmosphericNpcData use the same reviewed union-tag input
  gate before cache reuse. Missing or mismatched native inputs publish no rows.
  SpawnerConfig reaches whole-file status only through its sequential wave
  cursor; a uniquely matched suffix cannot close an unknown earlier field.
  Atmospheric NPC EOF framing can still contain opaque nested bodies.
- SkillData requires the selected current native root/action operation and the
  authenticated complete VFS source roster. Its source-bound family receipt is
  replayed afresh; the generated value plan cannot admit a root, field order,
  child grammar or union assignment by itself. Every encountered named object
  must match a current source-owned ordered program, every positive union tag
  must select that program's exact type, and root/available child field spans
  must agree with the independent raw reader. Each root requires all fields,
  its stored filename identifier, a complete raw byte partition and physical
  EOF. The formal builder refuses partial records before publication and never
  substitutes a derived-only decode or an old page cache.
  Unity curves retain their wrap modes and all named key words; null curves,
  null key arrays and empty arrays remain distinct. Scalars use their selected
  declared signedness. Unmanaged values use selected native instance offsets
  inside the independently proved raw copy, retaining all raw bytes including
  padding. Floating point words retain raw bits, including signed zero and NaN
  payloads. Typed dictionary entries preserve order and duplicate keys.
  Matching StringPool, native/Unity, complete raw-reader and source/receipt
  signatures remain mandatory at operation entry and exit. Missing or
  mismatched native inputs fail the required SkillData publication. Retained
  replay inputs live under the selected export's `meta/evidence/`; ordinary
  builds never take these inputs from temporary or report directories.
  `named_exact` describes authored storage, not runtime execution, callback
  selection, evaluated conditions or an observed skill transition.
- CharInteract always rebuilds its records; its dedicated root gate and whole
  current native graph must both pass. Each root requires all named fields and
  physical EOF. Native/Unity, complete raw-reader and selected-pool signatures
  must remain stable through the operation exit.
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
- Historical Buff action spans use the reviewed catalog's short or extended union header.
  Strictly contained spans are permitted; duplicates and crossing spans refuse
  publication. Containment does not establish action hierarchy or close the
  enclosing Buff schema. The census and action report must authenticate each
  other and the selected native inputs. The shared domain helper replays every
  selected codec against the physical source bytes and independently certified
  child spans; names, kinds, ranges and structural fields must match. Each route
  retains its own declared native input set.
  Current v9 spans instead replay the live current program: abstract actions
  include their dispatcher header, while concrete EffectActionData list elements
  begin at their own member count. The formats cannot substitute for each other.
- Buff roots follow the current canonical registry's family-report pin. Before
  cache reuse, the adapter authenticates that registry, the full family report,
  its reader and native input closure, and every exported logical source by
  path, length and digest. A complete row passes through its original root
  receipt and a separate named-value projection, including all child field
  extents and physical EOF. Missing, stale or incomplete required evidence
  refuses publication and preserves the last atomic dataset publication.
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
Whole InteractiveData, LevelScript and Template classification retains the
complete source-backed reader result. Summary-only rows from older readers
cannot supply decoded values. The page independently replays these families
through the complete current operation, sharing one authenticated ActionMap
graph where applicable. Native, source, StringPool and reader exit gates must
all pass before any pending records are published. A successful implementation
or focused probe does not substitute for a current full-corpus receipt.

- Publish a family's own reader boundary; never promote a partial frame to a
  complete one, and keep the frontend envelope unchanged.
- A family too large for one searchable catalog needs a versioned paged-catalog
  schema, not silent truncation.
- Add Characters deep links only after a decoder exposes an exact or explicitly
  typed character identity; filename resemblance is insufficient.

Animation publication uses one fresh complete operation over the selected
native root and reloaded matching StringPool. Every record retains all fifteen
ordered root fields and reached children, including source-named Beyond and
Unity keyframe words. Facts summarize actual controller hashes, mask names,
ExtraData type and known collection counts; raw words and complete child trees
remain in the reader payload. The legacy mask prefix cannot satisfy this lane,
and a partial result, opaque suffix or failed exit stops publication. The
post-exit receipt and attempted/closed owner counts stay in provenance; an old
prefix page cache is never an admission source.

The ordinary export preflight now produces the shared VFS audit and a separate
`meta/evidence/animestudio/jsondata_source_current.json` source inventory, with
its companion file ledger. This closes the shared missing-source-input gap for
current owner reads; it does not manufacture the named-classification registry.
Data additionally requests `jsondata-classified`. Its preparation runs
`memorypack.current_family_evidence`, then JsonData classification. The family
producer opens one selected current Sequence operation, proves Buff's root and
concrete component readers on the same native image, and joins every selected
Buff/Skill source to the independent inventory. The audited physical chunk MD5,
current overlay selection, exported logical bytes, reader sources and native
inputs must agree before publication. Source completeness grants no named
schema. Classification and page consumers independently replay the current
root and action receipts; saved JSON flags cannot replace the live operation.
This removes the selected Buff root / complete corpus dependency cycle on
first setup without activating historical formatter windows on a new build.
Family v2 manifests pin compact, per-file gzip JSONL ledgers. Producers stage
those ledgers until every native/source exit gate passes. Readers verify their
hashes, exact ordered source set and all canonical rows with bounded memory.
The v9 action manifest pins its Buff family and indexes source/action counts;
action bodies are read from that family's verified ledger. Classification and
Skill proof facts carry compact closure summaries rather than duplicating full
root object graphs; Buff and action payloads retain their named stored fields.
Current Buff roots include positive modifier, shield and timeline children,
with independent concrete-reader, processor-union and list-induction proofs.
SpecialAim positive lists retain their resource limit without treating it as
an element byte width. A whole Buff record requires all thirty named members,
the stored source ID and physical EOF; decoded children cannot promote a
stopped parent. Native refusal or an unknown positive child still withholds
whole-root status. The ordinary preparation regenerates these proofs and
receipts from selected installed/export inputs without diagnostic directories.
After opening child operations, the classifier restores a private native
validation scope owned by that live current operation. Each distinct selected
validator still proves its own program; only successful identical calls may be
reused within this run. Lazy parameter operations retain their own fresh
entry/exit proofs. These scopes close before the owning native, reader and
source bookends and before any classification report can be published.

These receipts and their cache live in the selected export's `meta/evidence/`.
Exact current input sets, source/reader/native hashes, complete family status,
registry replay and the page's independent admission gates still apply. A cache
hit requires unchanged implementation/declarations, selected sources and output
bytes; it rechecks family provenance and registry authentication. Interrupted
steps do not advance their cache or run dependent producers.
Within one page build the current Buff, Skill and action consumers share one
fresh native operation through an explicit context. Each still replays its own
report. The shared native, reader, pool, chunk and inventory exit gates close
before publishing the page index; no live proof survives into the next build.

Buff admission gates the current root, icon, dispel and component source proofs.
An updated icon contract alone cannot admit older formatter proofs. The Data
export's classified-evidence preparation requires both families to validate
before VFS auditing or publication; missing/mismatched native inputs fail the
export. The direct registry's unavailable-family projection remains a separate
diagnostic behavior and does not satisfy a successful Data export. A selected
export missing its entire game directory is rejected rather than published as
an empty Data page.
Source inventory remains separate from classification. Automatically preparing
evidence does not update native contracts or supply runtime observations.
