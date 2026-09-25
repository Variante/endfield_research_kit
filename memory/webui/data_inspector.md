# Data page (export stores and decoded datasets)

## Purpose

The Data page (`data-inspector`, after Assets in normal navigation) has three
modes. **Files** and **SQL** browse the export's SQLite stores -- every
exported Unity object document in `game/Unity.sqlite` and every packed game
file in `game/GameFiles.sqlite` -- as a file viewer and a read-only SQL console.
**Decoded** is the Decoded Data Inspector below: maintained decoder output
reviewed without a bespoke page per recovered format.

Files and SQL need the repository's `serve.py`, whose `/api/stores` endpoints
(`scripts/webui/data_inspector/store_browser.py`) answer bounded questions:
the stores and their groups, a filtered page of rows (name glob or substring,
object name, PathID, CAB), or one read-only statement with `inflate(data)` and
`doc(data, '$.path')`, capped at 500 rows and 15 s. Connections are read-only
with an authorizer refusing writes and ATTACH. Documents are fetched from the
URLs `serve.py` already answers from the stores, so the viewer shows exact
exported bytes: JSON as a lazy tree, text as text, anything else as hex. The
viewer reads no schema; PathID "find" is an index lookup, not a resolved
reference (a PPtr with a non-zero `m_FileID` points into another file). A
static package has no API and opens in Decoded mode. Assets no longer lists
exported JSON, because every such document is a store row here.

The rest of this guide is the Decoded mode contract.

Publishers cover two kinds of source. Families with a maintained
`scripts/game_data/` reader -- `AnimationConfig`, NPC montages, `LevelConfig`,
`LevelData`, `SkillData`, `CharInteractPerformCfgs`, `NavMesh`, `LevelMountPoint`, and the exact
single-instance config tables -- publish that reader's own result. Already
decoded Unity JSON -- AnimatorController and AnimatorOverrideController -- is
not copied wholesale: the builder publishes selected facts plus a mounted
`/export_full/` source link, and the browser loads a bounded raw preview only
on request.

The single-schema adapters route files to the same readers as
`scripts.game_data.jsondata_corpus`. SkillData uses a separate selected-native
generated-wrapper value reader: it publishes only after its own EOF and
identifier checks, and the independent SkillData VFS corpus remains the owner
of the narrower reviewed timeline-action framing claims.

The page is a general viewer, not a per-decoder layout: the frontend is taught
no decoder-specific schema, and every semantic it shows is recovered from the
published record's own shape.

The left pane is the shared list-page shell every other view uses -- sidebar
header with a filter-panel toggle and reset, collapsible `.filter-section` chip
groups built by `WebUI.filters.buildChips`, a draggable filter splitter, a
virtualized record list, the shared pager, and a draggable pane splitter. The
filter groups are data family, decode status, source folder, and tags; each is
multi-select and OR-matched, and with nothing selected every record is visible.
Source folder groups by the first three export segments, because a per-file
folder would be one chip per record and a coarser grouping would invent a
classification the publisher did not record.

The right pane shows scalar `facts` as quick-scan cards, then renders
everything the record published -- `facts` and `payload` both, as two labelled
roots -- in one annotated tree that preserves the publisher's own structure.
When a publisher supplies `references`, a separate section shows each stored
identifier and its exact source-field path. The SkillData publisher traverses
nested action values, including fail/succeed branches and options, and requires
the exact `AllowNextSkillAction` tag and type at each reference owner. Repeated
IDs at different source paths remain separate authored occurrences. Each item
names a target dataset
and record only after a filename-stem match; the browser checks that the target
is present in the loaded catalog before offering navigation. An absent or
ambiguous match remains a labelled non-link. The relation's publisher boundary
is displayed above the list, and these links make no runtime-use claim.

The two roots are different in kind, and the page must not label one as if it
contained the other. `facts` is the WebUI publisher adapter's own projection;
for an already-decoded JSON source it can hold far *more* than `payload`,
because the adapter computed it from the whole raw file. `payload` is what the
publisher republished of the decoder's output: the maintained reader's complete
result only when that reader produced it, and otherwise a selected part of an
already-decoded source whose mounted raw file stays authoritative. The required
`payloadKind` declares which one it is. A maintained reader's own
`status`/`schemaStatus` reports its framing when present; a reader that returns
values and a cursor leaves validation in the record status and publisher facts.
For such value-only readers, the header shows a fully consumed file only when
`facts.wholeFileCursorExact` is true and its `bytesConsumed` equals the source
size. An `evidenceBoundary` in publisher facts appears in the header as a
**publisher** boundary; it is never presented as a decoder claim. A decoder's
own payload boundary takes precedence when both are present.
No dataset id is hardcoded in the frontend. A publisher that republishes a
projection under `payload` must not report a framing status it did not
establish.
Only the decoder payload root receives framing chips. A publisher fact may quote
`bytesConsumed` or `serializedMemberCount` for quick scanning, but the facts
projection did not itself consume those bytes or deserialize those members.

Semantics are layered onto that structure by shape alone:

- a declared read order (`fieldOrder`, or a parent's `<key>FieldOrder`) orders
  the members it names and numbers them in that order; an order on a node that
  delegates to a `fields` child applies to the child;
- a member the order names but that was not published is shown as declared and
  not decoded, never silently omitted;
- keys the decoder published beside a declared order are marked as framing
  metadata instead of being mixed in with serialized members;
- byte ranges (`startOffset`/`endOffset`/`length`), member and row counts,
  `status`/`schemaStatus`, null frames, frame-closed state, Unity PPtr
  references, and `evidenceBoundary` become chips on the node that carries
  them, while remaining visible as ordinary children;
- integers published as decimal strings keep every digit and also show a
  hexadecimal form; hexadecimal is shown only for identity-like keys.

Field names are shown verbatim in every locale, never translated or
prettified. They are the decoder's own identifiers, and renaming one would make
its row unsearchable against the exported source, the contract JSON, and the
reader that produced it. Only page furniture and evidence vocabulary are
localized. For the same reason a token appears once: the record header already
carries the data family and decode status, so a publisher `tags` entry or a
`schemaStatus` that merely repeats one of those is dropped rather than
restated, and a reader that consumed the whole file states that on the file's
own size chip instead of adding a second chip with the same number.

A field search filters the tree to matching branches under a bounded row
budget, expand/collapse all is available (alt-click folds one branch
recursively), a raw-JSON view shows the same roots verbatim, and a bounded raw
source preview loads on request into its own section. Branches below the roots
materialize lazily, so a controller projection with thousands of hashes does not
build its whole DOM on select. AnimationConfig and montage payloads remain
complete maintained-reader results, while controller rows remain projections
with a raw JSON source link.

## Current dataset contents

| Dataset | Published detail |
| --- | --- |
| `animation-config` | Complete `frame_animation_config` result: framing/evidence status, member order and byte ranges, controller path ids, extra-data subtype and values, montage rows and clip data, NPC montages, sync-group curves, and time-reference curves. The overview also exposes scalar extra-data values and montage/curve names. |
| `npc-montage` | Complete `frame_npc_montage` result: root/data framing, clip information, named members, collections, decoded records, byte offsets, and evidence boundary. |
| `animator-controller` | Selected projection from the complete AnimeStudio JSON: layer/state/transition counts, condition tuples and occurrence counts, controller hashes grouped by source field, string table, idle-related names, curve fields, and compact object metadata. `Open raw source` is the complete JSON. |
| `animator-override-controller` | Controller reference, override/null counts, AnimeStudio metadata, and every original/override clip reference. `Open raw source` is the complete JSON. |
| `level-config` | Complete `decode_level_config` result: level identity and `idNum`, map id, seamless/dimension flags, level-data path hashes, and level grids. |
| `level-data` | `frame_leveldata_named_prefix` result for each source file: named exact fields and byte boundaries where reached, an explicit open field and opaque remainder elsewhere, and stored spline rows when their collection is decoded. Quick facts show the owning level folder, closed-field count, stop field, and spline/knot counts only when those rows were reached; `has-splines` and `has-knots` tags make positive files searchable. The decoded spline shape does not establish a movement route or runtime traversal. |
| `skill-data` | The selected build's `derived_values.decode_file` values for each exported SkillData file. A record is `structural_only` only when the native plan validates, the read cursor reaches EOF, and the stored `skillId` equals the exported filename; a failed file remains visible as `decode_error`. The status keeps nested union assignments at their structural evidence tier even with an exact cursor. The header shows the publisher's whole-file check and its structural-only boundary; quick facts and filters expose stored timeline/passive-event counts. `AllowNextSkillAction` (`0x000E`) rows, including those nested inside other action values, contribute stored `allowedSkillIdList` references with exact field paths. A unique filename-stem match opens another SkillData Inspector record; absent or duplicate matches stay unlinked. This is authored storage, not an observed skill transition. |
| `buff-action-receipts` | Optional, report-backed projections for BuffData files with selected `0x0092` CreateBuff or `0x00B4` FinishBuffAdvanced action receipts. Each record is `bounded_partial` and contains only authenticated action byte spans and generated-wrapper field names. The source file, nested values, unlisted actions, and complete BuffData schema are not decoded by this dataset. |

| `char-interact-perform` | Complete `decode_char_interact_complete_frame` result: the typed action union with per-type counts, audio actions, and the schema/union contract ids that name them. A file the complete frame rejects falls back to `frame_char_interact_prefix` and is published as a bounded row, never dropped. |
| `navmesh` | Per-level `decode_luna_area` and `decode_navmesh_state_container` results, framed to EOF. A NavMesh filename neither reader routes stays visible as `unsupported`. |
| `level-mount-point` | Validated `decode_level_mount_points` trees: sub-root types, node and mount-point counts, teleports, and tree depth. |
| `config-table` | Single-instance config tables that each have their own exact reader: teleport validation, `DialogIdTable`, aether-energy locks, matrix shockwave beats, gold coins, bamboo-raft tasks, mission areas, sub-game instances, the world-entity registry, and `InteractiveTable`. |

SkillData catalog entries also carry optional `searchTerms` for the type names
of direct action unions in `timelineActions[*]._sequenceActionData.actionData`
and `passiveEventActions[*].actions[*].actionData`. The detail publisher facts
group each exact stored tag/type pair and count its timeline and passive-event
occurrences separately. If either array shape differs, the optional inventory
is withheld as a whole; the decoded record remains available. Nested branch
actions are outside these counts and remain in the payload tree. The sidebar
search uses the catalog terms without loading detail shards. These are stored
union assignments, not observed action execution or verified runtime timing.
The detail's collapsed term section uses those same publisher terms as exact,
same-dataset filters. When the publisher also supplies a complete
`directStoredActionTypes` inventory, it shows each stored union tag and this
record's timeline/passive occurrence counts beside the type. The separate
`records` number counts catalog records that carry the term, never occurrences
or observed uses. Nested branch actions remain outside that inventory.
Selecting a term clears other list facets so the matching records are visible;
editing the search box returns to the normal regex search. A record without the
validated inventory keeps the generic Catalog terms view. The frontend does
not interpret the term's schema or promote its evidence tier.

For a record with that complete direct-action inventory, the detail also lists
each direct stored action at its decoded `timelineActions` or
`passiveEventActions` array indices, alongside its exact field path and union
tag. The frontend checks the payload's type/tag counts against the publisher's
inventory before offering locations; a changed or incomplete shape withholds
the list. Selecting one expands its exact node in the annotated structure.
These are array positions in stored values, not observed execution order or
timing; nested branch actions remain outside this direct-action list.

The Buff action receipt dataset is published only when the selected receipt
report matches the current Buff VFS corpus report byte-for-byte by digest,
the report's input and source identity sets agree, both selected native
contracts match the installed `GameAssembly.dll`, `global-metadata.dat`, and
`UnityPlayer.dll`, and every Buff source identity still matches its exported
logical bytes. Missing or changed evidence marks the dataset unavailable and
publishes no cached records. A record's collapsed span list locates each
verified wrapper in the projected tree by byte range; its fields retain the
reader's exact names and ranges. The list makes no claim about nested field
semantics, whole-file ownership, runtime execution, or trigger order.

A family is published here only when a maintained reader already owns it. The
adapter never softens that reader: status comes from the reader's own
`schemaStatus`/`status`, a reader that fails closed on an unsupported variant
produces a visible `decode_error` row carrying its reason, and a file no reader
routes is published as `unsupported` rather than omitted. The current corpus
publishes no such fail-closed row.

`GameplayConfig/LevelScriptTeleportValidationDataTable.json` is the one
teleport-validation table the client ships unserialized, as indented UTF-8 JSON
while its four siblings are MemoryPack. Its earlier `decode_error` ("table
member count changed") was a plaintext file dispatched to the binary reader,
never build drift. It now routes to `decode_teleport_validation_json_table`,
which proves the same ten row members, publishes the same row shape, and mounts
as `application/json`. A second container always gets its own reader here, never
a widened one.

Families deliberately still absent: LipSync has an exact reader but needs the
paged-catalog extension first, and LevelScriptData and complete BuffData
remain bounded/partial rather than fully understood. SkillData is included from the
selected native generated-wrapper plan only while that plan validates; missing
or mismatched native inputs publish an unavailable dataset with a diagnostic,
never cached rows from a previous build. The source signature includes the
selected native input hashes, so a client change cannot silently reuse old
SkillData shards. LevelData is included with its per-file exact or partial status
and open boundary visible. Terrain, Streaming,
irradiance volumes and BundleManifest decode to anonymous ranges with no
per-record identity worth browsing.

`extraDataFields` is intentionally only the list of decoded member names.
Their scalar values are in `extraDataValues`; every value, including nested
objects, remains under `payload.fields.extraData`. Montage and curve contents
are under `payload.fields.montages`, `payload.fields.syncGroupCurves`, and
`payload.fields.timeRefCurves`.

## Inputs and refresh

```bat
python -m scripts.webui.data_inspector.build_data_inspector
python -m scripts.webui.data_inspector.build_data_inspector --dataset animation-config
python -m scripts.webui.data_inspector.build_data_inspector --dataset level-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset skill-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset buff-action-receipts
python -m scripts.webui.data_inspector.build_data_inspector --force
```

The normal post-Story build graph runs the first command. Buff action receipts
are optional: the dataset requires the current generated Buff corpus and action
receipt reports under `reports/animestudio/`; explicit report paths are available
through `--buff-corpus-report` and `--buff-action-receipts-report`. A relative-path,
size, and modification-time signature reuses unchanged generated shards; this
is a build cache, not game-data evidence. `--force` bypasses it. The stored
signature must be compared through `contract.json_safe`, because publication
rewrites an integer outside JavaScript's exact range as a decimal string and
`latestMtimeNs` is always outside it -- comparing the raw value silently
rebuilt every dataset on every run. Source identity
and semantic claims still come from the selected export and the owning decoder.
Inspector data is local recovery output and is intentionally excluded from the
published WebUI archives; the debug page remains fail-closed when those local
datasets are absent.

## Publisher interface

New decoded families publish through
`scripts.webui.data_inspector.contract.publish_dataset`. Do not teach the
frontend a decoder-specific schema. The stable envelope is:

```text
webui/data/data_inspector/index.json
  schema: endfield.webui.decoded-data-root.v1
  datasets[]: id, title, description, available, diagnostic,
              recordCount, statusCounts, path

webui/data/data_inspector/datasets/<id>/index.json
  schema: endfield.webui.decoded-data-dataset.v1
  id, title, description, available, diagnostic
  provenance: sourceRoot, reader, publisherRevision, inputSignature
  catalog[]: id, title, status, summary, tags, sourcePath, shard
  shards[]: path, offset, count

webui/data/data_inspector/datasets/<id>/records.NNNN.json
  schema: endfield.webui.decoded-data-shard.v1
  datasetId, offset, records[]
```

Each record has these common fields:

| Field | Contract |
| --- | --- |
| `id` | stable and unique within the dataset; normally the export-relative source path |
| `title` | short human-readable identity |
| `status` | decoder result such as `named_exact`, `bounded_partial`, or `decode_error` |
| `summary` | compact searchable text, not the evidence payload |
| `tags` | compact filter/search tokens |
| `source` | `path`, mounted `href`, byte size, and media type |
| `facts` | optional selected domain values for quick review |
| `payload` | optional decoder output, republished as the publisher received it |
| `payloadKind` | required with `payload`: `reader` or `projection` (see below) |
| `references` | optional publisher projection: `evidenceBoundary` plus `items[]` with `kind`, `sourcePath`, `storedId`, `targetDatasetId`, `targetRecordId` (null if unresolved), and `targetState` (`present`, `absent`, or `ambiguous`); only a present target found in the loaded catalog becomes a link |
| `diagnostic` | bounded failure detail when decoding did not succeed |

All output is strict, browser-safe JSON. Integers outside JavaScript's exact
safe range are published as decimal strings so path IDs and hashes do not lose
digits in the browser. Decoder floats that are not representable in JSON are
published as the strings `"Infinity"`, `"-Infinity"`, or `"NaN"`; a producer
must not emit JavaScript-only numeric tokens.

`payloadKind` is how a publisher states who produced `payload`, and
`publish_dataset` fails closed on a record that carries a payload without it or
with a value outside the vocabulary:

- `reader` -- a maintained `scripts/game_data` reader returned this, so its own
  framing status and byte ranges describe it exactly;
- `projection` -- the WebUI publisher assembled it from an already-decoded
  source. It is a selected part, and the mounted raw file stays authoritative.

The browser labels the two differently, so a publisher must not declare
`reader` for something it assembled itself. The frontend still falls back to
sniffing the payload for a framing status, but only to keep a dataset published
before this field existed readable; a new publisher must declare it.

The catalog duplicates only fields needed to search and choose a record.
Domain data belongs in the lazy shard. A publisher may omit `payload` when the
source is already decoded JSON and too large to republish, but it must retain a
useful `facts` projection and a source link. Unknown, partial, and failed rows
remain visible; absence is never presented as successful empty data.

Dataset ids use lowercase ASCII letters, digits, `_`, and `-`. Records sort by
id for deterministic shards. A publisher must use the owning maintained reader
from `scripts/game_data/`; it must not duplicate binary framing in the WebUI
builder. Add a new raw-format reader and corpus gate in `scripts/game_data/`
first when no maintained decoder exists.

Increment the adapter's `publisherRevision` whenever its projection or
normalization changes. Cache reuse requires both that revision and the source
signature, so a reader/publisher code change cannot silently retain older
shards.

## Evidence boundary

The inspector does not promote evidence. A decoder's own `schemaStatus`,
`status`, ranges, diagnostics, and `evidenceBoundary` pass through unchanged.
Controller summaries are a convenience projection over decoded Unity JSON;
the raw mounted file remains the exact source. Search tags, filenames, and
character-like tokens are navigation aids only and do not establish ownership.

## Families a publisher adapter could still cover

The exact families in the table above are published. What remains is the
shortlist below, which records what a later session would otherwise re-derive
by walking `scripts/game_data/`. Reader boundaries are owned by
[`../game_data/extraction_payload_boundaries.md`](../game_data/extraction_payload_boundaries.md);
current file counts belong in `reports/animestudio/`, not here.

| Candidate | Owning reader | Why it is worth publishing |
| --- | --- | --- |
| LevelScriptData | `levelscript_binary` | the Story activation carrier; a named terminal suffix with weaker earlier framing, so `bounded_partial` rows would be visible as such |
| Complete BuffData | `memorypack.buff*` | the gameplay lane's open Buff family; the receipt dataset exposes two action wrapper interiors but not the reader's partial root cursor or opaque ranges |
| SpawnerConfig, Interactive, AtmosphericNpcData, LevelScriptTemplateData, MapConfig, UILevelMapLoadConfig, GPUISystemConfig, MissionRuntimeAsset | their matching `scripts/game_data/*_binary.py` / `*_json.py` readers | mid-size families with maintained readers and no page of their own |
| LipSync | `memorypack.lipsync` | an exact 15-member reader through EOF, but by far the largest JsonData family; it needs the paged-catalog extension below before it can be published |
| StringPathHash, FacBoneTRS | `extend_data_binary` | the global source-path catalog and facial-bone data; self-bounded, and useful for resolving path hashes seen in other records |
| Unity MonoBehaviour, PlayableDirector, TextAsset | already-decoded AnimeStudio JSON | the same projection-plus-source-link shape the controller adapters use; MonoBehaviour is the largest Unity family by far |

Not candidates: Terrain, Streaming/DynamicStreaming, irradiance volumes, and
BundleManifest decode to anonymous ranges rather than named records, so a
record list would carry no identity worth browsing; Audio, Story/Text Tables,
Map and Gameplay already have owning pages, and their evidence belongs there.

- Add publisher adapters as maintained decoders become reusable; keep the
  frontend envelope unchanged, and publish a family's own reader boundary
  rather than promoting a partial frame to a complete one.
- Add Characters deep links only after a decoder exposes an exact or explicitly
  typed character identity. Filename resemblance alone is insufficient.
- If a family is too large for one searchable catalog, extend the contract with
  a versioned paged-catalog schema instead of silently truncating records.
