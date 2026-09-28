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
| `skill-data` | selected-native generated-wrapper values | `structural_only` records after EOF and filename-id checks; stored `AllowNextSkillAction` references and direct-action inventories |
| `buff-action-receipts` | report-backed CreateBuff/FinishBuffAdvanced spans | optional `bounded_partial` span projections |
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

- A family is published only when a maintained `scripts/game_data` reader owns
  it. The adapter never softens that reader: status is the reader's own
  `schemaStatus`/`status`, a fail-closed variant becomes a visible
  `decode_error` row with its reason, and an unrouted file is `unsupported`,
  never omitted. A second container always gets its own reader, never a
  widened one.
- SkillData publishes only while the selected native plan validates; missing or
  mismatched inputs publish an unavailable dataset with a diagnostic, and the
  source signature includes the native hashes, so old shards are never reused
  across a client change.
- WebUI code never duplicates binary framing. A family without a reader gets a
  reader and corpus gate in `scripts/game_data/` first.
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
- SkillData references, search terms and occurrence lists are authored storage
  in stored array order; they establish no runtime transition, execution order
  or timing. Buff receipts locate verified wrapper spans only.
- Search tags, filenames and character-like tokens are navigation aids, not
  ownership.

## Focused refresh commands

```bat
python -m scripts.webui.data_inspector.build_data_inspector
python -m scripts.webui.data_inspector.build_data_inspector --dataset skill-data
python -m scripts.webui.data_inspector.build_data_inspector --dataset buff-action-receipts
python -m scripts.webui.data_inspector.build_data_inspector --force
```

The export freshness check covers only what the dataset builder reads (JsonData
and the animator controllers); served files are shown as exported. Buff receipts
need the current Buff corpus and action-receipt reports under
`reports/animestudio/` (`--buff-corpus-report`,
`--buff-action-receipts-report`). The build cache is keyed on the input
signature and publisher revision and is not game-data evidence; `--force`
bypasses it.

## Highest-value remaining gaps

Candidate families for a publisher adapter (reader boundaries are owned by
[`../game_data/extraction_payload_boundaries.md`](../game_data/extraction_payload_boundaries.md);
file counts belong in `reports/animestudio/`):

| Candidate | Owning reader | Why it is worth publishing |
| --- | --- | --- |
| LevelScriptData | `levelscript_binary` | the Story activation carrier; a named terminal suffix with weaker earlier framing, so `bounded_partial` rows would be visible as such |
| Complete BuffData | `memorypack.buff*` | the gameplay lane's open Buff family; the receipt dataset exposes two action wrapper interiors but not the reader's partial root cursor or opaque ranges |
| SpawnerConfig, Interactive, AtmosphericNpcData, LevelScriptTemplateData, MapConfig, UILevelMapLoadConfig, GPUISystemConfig, MissionRuntimeAsset | their `scripts/game_data/*_binary.py` / `*_json.py` readers | mid-size families with maintained readers and no page of their own |
| LipSync | `memorypack.lipsync` | an exact 15-member reader through EOF, but the largest JsonData family; it needs a paged catalog first |
| StringPathHash, FacBoneTRS | `extend_data_binary` | the global source-path catalog and facial-bone data; self-bounded, and useful for resolving path hashes seen in other records |
| Unity MonoBehaviour, PlayableDirector, TextAsset | already-decoded AnimeStudio JSON | the projection-plus-source-link shape the controller adapters use; MonoBehaviour is the largest Unity family |

Not candidates: Terrain, Streaming/DynamicStreaming, irradiance volumes and
BundleManifest decode to anonymous ranges with no per-record identity; Audio,
Story/Text, Map and Gameplay data belong to their own pages.

- Publish a family's own reader boundary; never promote a partial frame to a
  complete one, and keep the frontend envelope unchanged.
- A family too large for one searchable catalog needs a versioned paged-catalog
  schema, not silent truncation.
- Add Characters deep links only after a decoder exposes an exact or explicitly
  typed character identity; filename resemblance is insufficient.
