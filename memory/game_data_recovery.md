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

MissionRuntime is one case where VFS-root precedence is semantically material.
StreamingAssets and Persistent currently expose the same 980
`MissionRuntimeAsset` filenames, but five payloads differ (`f1m19d3`, `f1m32`,
`hidden59`, `hidden62`, and `sm2l8m1`). Persistent contains the current
authored overrides. Active consumers now use it only when its filename set
covers the complete StreamingAssets base set; an incomplete Persistent tree
causes a whole-corpus StreamingAssets fallback instead of a per-file hybrid.
Generated Mission Pipeline provenance records the selected root, decision,
base/override counts, missing base files, extra override files, and the exact
common filenames whose bytes differ. Explicit `--mission-root` builds are
labeled separately.

All maintained offline Story-recovery audits that consume authored
MissionRuntime now use the same complete-Persistent-or-whole-Streaming
selector. This prevents the WebUI builder, property audits, protocol census,
option scan, and mission-order evidence tools from silently reasoning about
different versions of the same five files. The effective corpus contains
3,496 typed tracking rows on 3,241 objectives and 217 mission-property rows
across 71 missions. Tracking filters and initial property values are authored
configuration; without a decoded consumer/writer bridge they remain context
and do not create mission, quest, playback, completion, or ordering edges.
The current client does expose the read/update half of that bridge:
`SimpleConditionCheckMissionVariableInt` reads
`MissionData.propertyDict(missionId, missionVarName)`, compares it with the
authored operator/target, and listens for the global change event.
`SC_UPDATE_MISSION_PROPERTY (124)` resolves numeric property ids through
`MissionPropertyKeyIdTable`, converts each `DYNAMIC_PARAMETER`, updates the
dictionary, and broadcasts the event. This proves server-synchronized
tracking visibility, not the missing server-side producer or change timing.

The current binary-first system-carrier audit demonstrates the intended
cross-layer standard. Three typed DomainDepot tables plus native request/reply
handlers prove 24 residual f1m25 dialog bindings; one SkipChapter row plus its
native sender/handler proves one e5m1 dialog binding. A
FactoryBuildingPanelLock row proves only a local two-quest-state radio
dependency and creates no owner. The strict Mission Pipeline result is now
4,072 connected of 5,282 unique Story files, leaving 1,210 unlinked.

The current DialogTree pass adds four exact non-owning dependencies without
changing those ownership counts. It requires exact sequential MemoryPack
registration in the first 2,633-entry `DialogIdTable` map, a typed registered
DialogTree asset, exact connection-component reachability to a same-root
numeric trunk, and typed `CheckQuestState` fields. Installed native consumers
prove local cache comparison and If/Branch route selection; no direct packet
belongs to that evaluation. The parser fails closed on duplicate node ids,
wrong or dangling connection records, dynamic/missing comparers, and nonnumeric
same-prefix trunks.

The installed binary also proves two true DialogTree playback carriers.
`DialogTreeTrunkNode._actorNodeData.mfTrunkActionData._trunkId` flows through
`DTTrunkNodeData.get_trunkId` (token `0x06003977`, VA `0x187292f78`),
`DialogTreeTrunkNode._DoPlayTrunk` (`0x06003bb6`, `0x1872a80b8`), and
`DialogManager.PlayTrunkNode` (`0x0600f785`, `0x186e16cc8`).
`DialogTreeDialogNode._dialogId` flows through its `DoExecute`
(`0x06003b6e`, `0x1872a3770`) to `DialogManager.PlayNextDialog`
(`0x0600f78e`, `0x186e168e8`). These are local client playback paths with no
request/reply. Authored trunk ids remain only reachable possibilities because
`FindTrunkIdForReplacement` (`0x06003bb3`, `0x1872a76f8`) and
`DialogPlayTrunkActionData.SetOverrideTrunkId` (`0x06003955`, `0x187297578`)
can replace them at runtime.

Native graph entry semantics now support a distinct prime-node dependency
tier. `DialogTreeController.StartDialog` (`0x06003a9b`), both `StartDialogue`
overloads (`0x06003a92`/`0x06003a96`), `Graph.StartGraph` (`0x06001120`),
`Graph.get_primeNode` (`0x06001109`), `DialogTree.OnGraphStarted`
(`0x06003a77`), and `DialogTree.EnterNode` (`0x06003a75`) prove that a fresh
graph falls back to serialized `allNodes[0]`. They do not prove that a quest
starts the parent dialog or visits every reachable child. The maintained join
therefore records only possible local containment plus an exact parent-dialog
completion dependency, with no ownership, quest playback, or server exchange.
It additionally requires exact current `DialogTextTable` trunk ids, registered
child dialog ids, one parent root, and complete typed connection integrity.

The current FMV schemas are also exact. MemoryPack action `0x035e` has 14
members and serializes `PlayFmvAction._moviePath` as derived member 9;
`0x04a1` has 16 members and serializes
`StartFmvAndTeleportAction._fmvId` as the final derived member. The installed
LevelScript corpus contains 36 such records (33 PlayFmv and three
StartFmvAndTeleport), all with exact `cs_video_*` identities. Mission placement
is accepted only when every occurrence for a Story key resolves through
validated LevelData to the same mission shell. These actions are local
presentation and serialize no mission, quest, request, or expected reply.

The maintained extractor requires exact sequential DialogIdTable registration,
an exact matching DialogTree asset name, typed resolved connections, and a
directed ancestor/descendant path to a same-root numeric trunk anchor. It
ignores missing-id nodes as unaddressable authoring remnants: 199 of 2,579
registered assets contain 307 such nodes, while the audited corpus has zero
duplicate nonempty ids and zero unresolved connection endpoints. A missing-id
node can never be an anchor or carrier. `CheckTalkOptionFinish._dialogId` is a
completion dependency and may not create a playback link.
`DialogLeftSubtitleActionData.text1..text4` is instead decoded as a distinct
local-presentation relation: the current exact occurrence binds the two
`black_e0m2_1` LangKeys through parent `dlg_e0m2_4` to the e0m2 mission shell,
while explicitly denying black/audio playback, quest placement, chronology,
and a network exchange. The trunk/dialog playback boundary promotes 13 Story
files through 66 typed occurrences; after the separate SM1 world-interactive
context below, no typed DialogTree playback file remains unscoped. The last two
children use stricter child-specific context: a no-bypass all-leaf a1m5
`CombineCondition` quest-state gate, and one sm2l2m1 q10 tracked proxy joined
through exact proxy tables/registry to a registered parent and typed
`PlayNextDialog` child. Both remain possible local routes, not ownership or
guaranteed playback.

The same audit rejects broader-looking joins when the runtime consumer does not
carry the required semantics. Seventy-five currently unlinked NpcProxyEx
dialogs share exact proxy ids with MissionRuntime tracking rows, but proxy ids
are reused across missions and `NpcProxyTrackingInfo.GetTargetPos` calls only
`TryGetProxyByProxyId` plus `GetAoiPosition`; dialog selection lives on the
separate NpcProxy/NpcInteract path. The completed native trace now proves that
path exactly: `SC_NPC_ENTER_MAP_RESYNC` or `SC_NPC_ACTIVE_CHANGE_NTF` supplies
`SCD_NPC_PROXY_INFO.activeCondIndex`, the client selects
`NpcRuntimeProxyData.exDatas[index-1]`, and
`_TryGetNpcProxyInteractDialogId` reads only `dialogId` at row `+0x28`.
Adjacent `missionId` at `+0x30` is used separately by `OnDeActive ->
_IsMissionConflict` to read `MissionData.isPaused`. Of 2,630 total rows, 1,008
carry a dialog and 453 also carry a mission id, but all 138 currently unlinked
placements (126 Story files) have a blank mission id. The server pushes carry
proxyNumId/metaKvs/activeCondIndex, not mission, quest, or dialog identity, so
the broad proxy-id coincidence still adds zero bindings. The one accepted q10
navigation relation above requires substantially more independent structure:
one typed tracking occurrence and scene, one exact registry identity/position,
one missionless proxy configuration with a sole nonempty registered parent,
and one typed parent-to-child DialogTree route. Six PRTS matches prove level context only,
49 SNS rows have no authored mission id, and 13 audio-event rows have no owner
field. These remain rejected candidates, not weak bindings.

`NpcProxyTable.lazyDestroyOverrideDialogId` is a distinct executable carrier,
not part of the rejected `NpcProxyEx.activeCondIndex` selector. The current
table has three nonempty configurations. Only
`lanshan_map02_v1d4d0_003` combines `lazyDestroy=true`, exact scene
`map02_lv008`, `dlg_sm2l7m1_18`, and one typed same-scene consumer
(`sm2l7m1_q#17`). Installed native code closes the field path:
`NpcProxy.OnDeActive` (`0x187069e7c`) calls
`NpcProxyMgr.ApplyLazyDestroyData` (`0x187065af4`), which reads
`NpcRuntimeProxyData+0x258` and calls
`NpcManager.AddOverrideInteractDialogId` (`0x18705f854`) with priority 2.
This proves executable lazy-destroy dialog configuration and supports a
non-owning quest-context edge only. The server-pushed proxy state has no
mission/quest/dialog id, the client sends no request for this action, and the
data does not prove that the quest triggers deactivation or playback.

The exact interactive-progress carrier closes another bounded native gap. It
requires every Story occurrence to be rooted at a constant current-build
`OnInteractiveStateChanged` entity, directly or through an exact literal
`RaiseCustomScriptEvent` producer. That entity must resolve to one mirrored
counted LevelInteractiveData record carrying a complete
`SimpleConditionCheckQuestState(Equal, Completed)` progress lock, match the
WorldEntityRegistry type/detail pair, and resolve uniquely to one real
MissionRuntime quest; every occurrence must agree. The current data yields
eight `sm2l5m1` Story context rows (seven q1, one q8), six of them net-new in
coverage. Native dispatch is local. The quest state gates interactive config;
it does not prove ownership, quest activation/playback/completion, a request,
or an expected reply.

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

A full targeted installed-VFS Lua extraction currently yields 1,290 modules
(one unrelated invalid Markdown entry in the Lua block is not payload data).
The extraction matches the current installed Lua chunk (`22097503`, MD5
`1586E385D1FDD76F3C881648007C918A`). No authored `black_*` Story id occurs in
that corpus. Across the current Mission Pipeline gap it contains zero of the
182 residual native-playback Story ids and zero of the 106 residual listener or
target LevelScript ids. Only two of the then-current 1,303 unlinked Story ids
occur:
`cutscene_e1m10_1` in `PhaseGenderChange.lua` and `cutscene_e0m0_1` in
`PhaseGenderSelect.lua`. Both are exact system-phase `GameAction.PlayCutscene*`
consumers, but neither module carries a mission, quest, or LevelScript identity,
so they classify playback without creating mission ownership. The exact local
black-screen runtime route is likewise generic:
`CinematicSystem._DoAction` dispatches `NarrativeBlackScreen` to
`GameAction.ShowNarrativeBlackScreenByHandle`, and `RadioSystem` only waits for
`ON_NARRATIVE_BLACK_SCREEN_END`. This proves local presentation sequencing but
supplies no mission/quest identity. Selected world-streaming chunks and
`ExtendData/CompressData.bin` likewise contain no exact cold black Story ids;
these negative probes must not be promoted into ownership.

`CompressData.bin` is no longer an opaque/raw-byte negative. The current
789,844-byte file (SHA-256
`64CF8201577FA24E4B462CB6794A95574E3AC22DA8EC7B33F443593A1FBDA141`)
has an exact validated layout:

```text
recordCount:uint32
absoluteOffsets:uint32[recordCount]
record[recordCount]:
    compressedLength:uint32
    originalLength:uint32
    brotliPayload:byte[compressedLength]
```

`DataCompressManager._GetSpanByIndex` reads this exact offset plus
length-pair shape, `GetCompressBinary` calls `BrotliDecoder.Decompress`, and
the runtime writer calls `BrotliEncoder.Compress`. All 290 current records
decode to valid UTF-16LE JSON totaling 15,960,452 bytes, and every root object
is `NodeCanvas.BehaviourTrees.BehaviourTree`. The serialized join is
`_enableGraphStringCompress` plus `_serializedGraphStringIndex`: 569 typed
BehaviourTree assets consume all 290 pool indexes, with shared indexes
representing deliberate deduplication; one small control asset retains inline
JSON. The pool is therefore AI behavior configuration, not a general opaque
registry. See
`reports/story/recovery/compress_data_story_audit.{json,md}` for the exact
record/object map.

Two other current ExtendData-family files are the resource reverse
registries `Main/StringPathHash.bin` and
`Initial/InitStringPathHash.bin`. Both use the same validated
`bucket bytes + (hash:int64, stringPoolOffset:uint64) entries + length-prefixed
UTF-16LE pool` layout. The main registry contains 538,806 entries; the initial
registry contains 1,659. The initial registry contributes zero paths for the
three unresolved CutsceneRoot selector keys, while the main registry
contributes all 34. The exact-consumer census also searches both endian forms
of those 34 hashes through the current 280,436,712-byte `GameAssembly.dll` and
finds zero literal occurrences. This closes hard-coded native hash consumers,
but not dynamically computed hashes or runtime/server-provided selectors.

The final current file,
`Main/FacBone/FacBoneTRS.bin`, is also decoded completely. Its 2,020-byte
serialized unit hash table maps 84 signed unit GUIDs to 762 bone records; the
bone records map 64-bit bone-name hashes and frame indexes to 279,615
contiguous 64-byte matrices. The matrix region ends exactly at the
17,909,576-byte EOF and contains no non-finite `float32` values. Native
`FacBoneTRSBinary.TryGetBoneTRS` confirms the exact
`guid -> boneNameHash -> frame -> matrix` lookup, and
`STATICVATDATA.GetBoneTRS` supplies the entity's current VAT frame and a
`StringHash64` of the requested bone name. See
`reports/story/recovery/facbone_trs_story_audit.{json,md}`.

The current ExtendData/InitialExtendData inventory is therefore exhaustive:
one initial resource-path registry and three main files comprising the main
resource-path registry, the compressed BehaviourTree pool, and the factory
bone-transform table. These conclusions are build-specific and do not cover
runtime-added data, server state, or future files.

The separately skipped BundleManifest is a Brotli-compressed typed resource
index. The current effective Persistent `manifest.hgmmap` expands from
46,476,082 to 137,818,624 bytes and validates as:

```text
HEAD1 + UTF-16 manifest hash
HEAD2 + UTF-16 hash-version string
UTF-16 perforce CL
length + asset hash-table blob
length + bundle hash-table blob
length + bundle-array blob
length + shared data pool + matching trailing length
```

The current asset table has 327,584 24-byte records; the bundle dictionary and
array each have 237,800 48-byte records. Every non-empty hash bucket partitions
its record region without gaps or overlap, and the shared data pool consumes
the framed remainder exactly. Native metadata identifies the logical fields as
asset path/hash, bundle index/size, bundle names, dependency sets, flags,
hashes, and category. It is a loader routing/dependency registry, not an
authored mission/quest activation table. See
`reports/story/recovery/bundle_manifest_story_audit.{json,md}`.

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
- LevelScript ActionBase/ActionHeader union tags `<= 0xf9` use one tag byte;
  larger tags use `0xfa` plus a little-endian u16. The next byte is the concrete
  subtype member count and the following common ActionBase byte is the
  `dontLog` bool, which valid records serialize as either `0` or `1`. Treating
  `dontLog=1` as an invalid extended record shifts the boundary by two bytes and
  creates a false compact tag. Both maintained LevelScript parsers now expose
  `unionTag`, `serializedMemberCount`, `dontLog`, and the tag encoding while
  retaining the old combined `code/kind` fields only for report compatibility.
- Generated MemoryPack wrappers and GameAssembly deserializer setter order are
  stronger schema evidence than field declaration order alone.

The installed `ActionHeaderForMemoryPackFormatter..cctor` now has a complete
native audit: 230 contiguous union registrations `0x0000..0x00e5`, recovered
from `GameAssembly.dll` and named through `global-metadata.dat`. The maintained
table is used only for records proved to belong to `headerList`. `ActionBase`,
`PureGetter`, and `ActionHeader` reuse the same numeric tag space, so applying a
header name to an unclassified record would be a type collision rather than a
recovery. The generated evidence is
`reports/story/recovery/memorypack_union_formatter_tag_audit.{json,md}`.

Not every native data class uses MemoryPack. DialogTree TextAssets use
ParadoxNotion named JSON inside base64 `m_Script`. Narrative-mask actions are
discriminated by exact `$type` strings, so member order and omitted default
members are not byte-schema evidence. The installed binary gives
`DialogNarrativeMaskActionData.texts` at runtime offset `+0x40` and action enum
125; `DialogComplexNarrativeMaskActionData.textDataList` is also at `+0x40`
and its action enum is 144. `UICommonMaskData.textDataList` is at `+0x70`, while
`CommonMaskTextData` embeds `LangKey` at `+0x10`, `textBeforeTime` at `+0x20`,
`_useCustomText` at `+0x24`, and `customText` at `+0x28`. The authored JSON
extractor accepts only the exact DialogTree root, typed node action containers,
concrete action `$type`, and LangKey field; recursive text search, literal
stage directions, and custom text cannot create graph relations.

These rules enabled exact recovery of `SelectorData`, `TargetSettings`,
`DirectionSettings`, `FindTargetAction`, and `ContinuousFindTargetAction` in
the BuffData corpus. Every current FindTarget occurrence decodes exactly; the
remaining ambiguous BuffData chains are blocked by other action families, not
selectors. Two selector subtype payloads remain intentionally unsupported
until samples exist: `ShapeFinder+Data` and `PriorityFilter+Data`.

The current native `LevelDataForMemoryPack.Deserialize` enforces 43 members
(`0x2b`), not the older 42-member working list. Serialized member 22 is
`Dictionary<ulong, LevelScriptBriefData>` and member 23 is
`Dictionary<ulong, string>`; runtime `levelScripts` is not serialized.
`LevelScriptBriefData` enforces eight members in this order: `dataPath`,
`levelScriptType`, `maxStage`, `parentLevelScriptId`, `properties`,
`propertyIdToKeyMap`, `refWorldEntityIdList`, and `scriptId`. The maintained
Story join parses the complete nested value, requires final `scriptId == key`,
requires all entries to form one contiguous chain, and verifies the signed
dictionary count immediately before that chain. Across mission-named current
LevelData this recovers 2,256 exact entries; the former bare-u64 scan admitted
seven false host rows. A mission-shaped LevelData filename is asset-shell
context only, not logical mission or quest ownership; explicit MissionRuntime
conditions remain the stronger consumer edge.

LevelData member 17 also contains an exact positive state/playback carrier.
`FunctionAreaSpecificData` union tag `9` selects the seven-member
`RadioTriggerZoneData`; the maintained decoder requires the immediately
preceding `specificDatas` count to be exactly one and parses the native
alphabetical member order `hideAfterMissionId`, `hideBeforeMissionId`,
`hideCompleteMissionId`, `prtsId`, `radioId`, `triggerId`, and
`useRadioTriggerOnce`. Four current rows pass every guard and produce six
mission-state placements for four radios. The native
`RadioTriggerZoneHandler.OnEnter` consumer calls
`_GetRadioTriggerMissionState`, which invokes `MissionSystem.GetMissionState`
for the three mission fields, then reaches `GameAction.PlayRadio`. This proves
state-gated local playback context. It does not prove quest ownership, and it
does not create a client request or paired server reply; the mission cache is
populated by independent synchronization pushes.

LevelData member 20 now has a narrow exact narrative-interactive decoder. It
accepts only a counted list of 25-member `LevelInteractiveData` records, uses
the next typed record as the current record's end boundary, and fully decodes
the installed string ParamValue map rather than scanning a byte window. Two
current c16 records uniquely co-carry `FX_CHANGE_MISSION_ID=c16m4d5` and
`TYPE_ID=rp_radio_c16m4_50/51`. The popup table, byte-identical InteractiveTable
mirrors, exact `int_narrative_common` template union tag `0x00b3`, and installed
NarrativeComponent state-query/playback bodies complete the original-data
consumer chain. The result is a mission-state FX/playback dependency, not an
interactive's mission owner. Other framed ReadingPopUp consumers without a
mission key remain consumer-only evidence.

The same exact framing now recovers narrative configuration even when no
mission-state PropertyKey shares the record. StreamingAssets and Persistent
LevelData bytes must match exactly, the record must end at the next typed list
item, component key `94` must contain the complete `type_id` ParamValue map,
and the entity must resolve through byte-identical InteractiveTable mirrors to
an `int_narrative*` template. A direct Story id or exact
`ReadingPopUpTable.contentId` join then supplies source-configuration context.
The current corpus has 20 placements for 19 unique Story keys in four
LevelData assets. The final item of every list remains excluded because the
next top-level LevelData member is not borrowed as an inferred boundary.
These rows establish the LevelData asset, narrative entity, and configured
Story consumer; they do not establish availability, player interaction
timing, mission/quest activation, ownership, or relative Story order.

Top-level `LevelScriptData` itself is a current 27-member MemoryPack object,
not the older 26-member working model; the omitted current field was
`enablePreload`. The newly decoded `interactives` member
is a counted map of fully bounded 25-member `LevelInteractiveData` values.
The maintained parser consumes each complete record, validates the
script-id/trigger-volume tail, requires a narrative InteractiveTable template,
and decodes component key `94` as an exact PropertyKey-to-ParamValue map.
`type_id` may name a Story key directly or a `ReadingPopUpTable` row whose
`contentId` names the Story key. This recovered 145 exact placements for 131
unique Story keys across 50 mission files. It is exact authored source
configuration and local narrative-consumer identity; it does not establish
script activation, player interaction timing, quest causality, ownership, or
relative Story order. Same-script MissionRuntime conditions are retained only
as explicit context.

The remaining native-playback audit also closes three tempting but invalid
ownership shortcuts. All 174 distinct residual `(levelId, scriptId)` pairs
have valid member-22 BriefData entries, but every residual
`parentLevelScriptId` is zero.
Serialized member 23 is an exact `Dictionary<ulong, string>`, yet its count is
zero in all 665 nonempty parsed LevelData blobs. `LevelConfig.m_levelDataPaths`,
`LevelData.LoadLevelDataFromLevelConfig`, `MergeData`, and
`LevelScriptManager.OnLevelLoaded` prove level loading/registration only; they
do not introduce a mission or quest owner.

The same complete dictionary now supports a fail-closed exclusion check for
unresolved native receivers. `storyTriggerManifest.nominalMissionId` remains a
filename/index candidate only, but if a same-level mission-named LevelData file
exists, its validated member-22 dictionary can prove that the candidate
receiver script is absent. The current v8 activation-frontier report finds 49
such receiver scripts. This closes the static nominal-mission host route
without treating absence as proof of some different owner. For the five
unresolved exact-playback black keys, three are excluded by their candidate
mission hosts; the other two have exact activity SubGame `bindScriptId`
carriers and no same-level nominal-mission host. No graph edge is emitted.

An independent exact asset-shell join is available through mission areas.
Typed `MissionAreaTrackingInfo.missionAreaId` values in MissionRuntime resolve
through `MissionAreaTable.subDataParentId`; when that exact u64 is a root key in
the same fully validated member-22 dictionary, the file's requested script
entries inherit mission-area shell context. Every authored parent-root hit in
the file and every matching file must resolve to one MissionRuntime. Shared
roots remain rejected; the current c13 root is correctly ambiguous between
`c13m2` and `c13m2d5`. LevelData filenames do not participate in this join.

The same validated member-22 dictionary can scope a sibling playback script
when the complete LevelData shell contains authoritative original-data anchors:
an exact MissionRuntime script reference, a typed MissionArea parent root, or
an exact mission-shaped LevelData asset identity. All anchors across every
matching container must union to one mission; otherwise the shell stays shared.
This recovered 17 current evidence rows, including 14 previously unlinked Story
files, as mission-shell asset context only. It does not assign a quest or imply
that an anchored script triggers every sibling script.

Typed `Beyond.Gameplay.EntityTrackingInfo` supplies a separate native runtime
join. The installed metadata exposes `trackScriptEntity`, `entityLogicId`,
`scriptId`, and `entitySlotId`. `get_scriptIdGlobal` reads inherited `sceneId`
and the local script id, then calls `GameUtil.ToGlobalId`; the current binary
implements `levelNum * 100,000,000 + localScriptId`. The global-id/slot pair is
resolved through `EntityManager.TryGetScriptEntityLogicIdBySlotId`, with
`WorldEntityRegistry.TryGetScriptEntityInfo` as the static fallback used for
position lookup. The exported registry stores aligned
`m_scriptEntityIdList` / `m_scriptEntityBriefInfo` arrays, so the maintained
join requires equal lengths, one exact script/slot row, and the matching global
LevelScript file under the authored `sceneId`.

MissionRuntime also nests this same exact type inside authored
`multiDescTrackingInfoList[].actualList[]` wrappers. The maintained extractor
accepts those rows only when `mapTrackingToMultiDesc` is true, the wrapper and
actual list are structurally exact, the child is `EntityTrackingInfo`, and the
union of every typed owner source is exactly one mission. This recovers five
same-script navigation-context radios for `c27m4d5_q#14` through global script
`26900000008`. It also resolves `c33m1_q#10` through global script
`2100600007`, registry slot `40001`, `int_narrative_empty`, the exact
interactive-object table mapping, and the serialized `type_id` property
`dlg_c33m1_17`. Both joins are configuration/navigation context only; no quest
playback, ordering, completion, or server exchange is inferred.

This proves the quest's navigation target, not a quest-to-Story playback edge.
The native `InteractiveTable` reader now validates its complete two-member
layout: the core-template path map followed by the interactive-object to
template map, with the StreamingAssets/Persistent copies required to match.
Only registry objects whose exact table template is `int_narrative_mission`
may expose the serialized `interactives[entitySlotId].properties[type_id]`
Story id. The current pipeline has 25 such evidence rows. Arbitrary file
strings, template-name guesses, and cross-script getter records are rejected.
A typed Story action in the same resolved script is retained only when it
belongs to `actionList` and has an exact serialized event/control path, and it
remains same-script context unless a separate native edge bridges the tracked
entity slot to that event. This distinction is visible in `sm2l3m4_q#1`: the
tracked slot is `40002`, while the dialog playback control path is entered
through trigger slot `80001`.

One current route does contain that missing bridge. For `e0m0_q#2`, the tracked
travel-pole slot is the exact `ScriptEntityPtr` operand of a typed
`EntityCompare` getter used by an `IfElseAction` on
`LevelEvent_OnTravelPoleBegin`; the true branch runs
`RaiseCustomLevelEvent("PLAY_SEQ_1")`, and one same-level
`LevelEvent_OnCustomEvent` listener plays `cutscene_e0m0_1stZipline`. This is
exact client playback context. The quest condition is still
`GameConditionServerPlaceHolder`; the synchronized objective packet is now
known, but the server's completion rule and any link from that rule to the
local playback remain opaque.

Non-script `EntityTrackingInfo` uses a distinct fail-closed bridge. Its local
`entityLogicId` suffix is grouped against current
`WorldEntityRegistry.worldEntityBriefInfos`; exactly one global id must exist.
An exact constant-target `EntityEvent_OnSavePropertyChanged` header can then
match that global id only in the authored scene. The current join resolves
`e8m1_q#12` local `83108` to global `23400083108`, property `state`, and an
exact control path to `radio_e8m1_12`. The listener is local and the objective
is `GameConditionServerPlaceHolder`, so this remains navigation/property
context rather than a completion or server-return claim.

The same non-script tracking surface now has one stricter world-interactive
Dialog bridge. The decoder accepts only a counted, next-record-bounded
25-member LevelInteractiveData record, locates `componentProperties` at the
installed inherited-prefix boundary, and fully decodes component key 94's
heterogeneous ParamValue map. The map must have exactly
`FX_CHANGE_MISSION_ID`, `TYPE`, and `TYPE_ID`; the first and third are exact
String values and `TYPE` must be Int value `1` (`NarrativeInteractType.Dialog`).
The builder then requires one MissionRuntime tracking row, one matching global
WorldEntityRegistry identity, same entity type/detail id, byte-identical
StreamingAssets/Persistent LevelData, InteractiveTable, and template files,
and the exact `int_narrative_common` template mapping. Current data resolves
only `sm1l1m1_q#6 -> 2100070023 -> dlg_sm1l1m1_17`; the typed DialogTree path
then gives `dlg_sm1l1m1_16` one possible authored child route. This is local
navigation/configuration context, never ownership, quest playback/completion,
chronology, or a server exchange.

The current installed-build binary and complete MissionRuntime corpus now give
a fail-closed model for `GameConditionServerPlaceHolder`. The audited
`GameAssembly.dll` SHA-256 is
`0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE` and
the matching `global-metadata.dat` SHA-256 is
`90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E`.
The type owns `_comparer` and `_progressToCompare`; its installed fallback
`get_conditionType` at `0x18479ec70` returns `int.MaxValue`. The StartQuest
callback binder at `0x183a89700` retains a `ResultChange` callback only for
`ConditionType.ClientOnly=9999`, so this fallback does **not** send
`CS_UPDATE_QUEST_OBJECTIVE` (message 314). IFix patch id `0x5605` can replace
the fallback in principle, but the current installed patch path is now audited.
StreamingAssets contains an empty 73-byte IFix block, while Persistent supplies
one logical `Data/IFixPatchOut/Windows/Gameplay.Beyond.patch.bytes` payload
(82,021 bytes after VFS decryption, SHA-256
`737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21`).
Its 30 signature targets match none of `0x5605`, inherited OnActivate
`0x54d1`, or OnDeactivate `0x54d2`. The effective current behavior is therefore
the `int.MaxValue` condition type plus no-op server-condition activation and
deactivation. Future installed patches still require a fresh fail-closed audit.

The mission protocol boundary is asynchronous rather than request/response
shaped. `CS_ACCEPT_MISSION` message 315 carries only `missionId` and has no
paired `SC_ACCEPT_MISSION`; the client waits for `SC_MISSION_STATE_UPDATE` 112.
Only the proven `ClientOnly=9999` callback path sends absolute
`CS_UPDATE_QUEST_OBJECTIVE` values with `isAdd=false`, after which
`SC_QUEST_OBJECTIVES_UPDATE` 116 and `SC_QUEST_STATE_UPDATE` 111 are separate
server pushes. `CS_FINISH_DIALOG` 341 carries dialog id, selected options,
finish numbers, extra-info type, and optional submit info; `SC_FINISH_DIALOG`
131 is an asynchronous confirmation echo and the schema has no correlation
UUID. `CS_FAIL_MISSION`, `CS_MISSION_EVENT_TRIGGER`, and
`CS_MISSION_CLIENT_TRIGGER_DONE` exist in the protocol schema, but no active
non-protobuf fallback sender was recovered from the installed binary. They
must remain protocol-capable with sender unconfirmed, not active graph edges.

The same IFix payload contains 86 exact `dlgtl_*` strings across 16
mission-shaped families, but its patched target is specifically
`CinematicTimelineManagerBase._TimelineAsyncCompileProcess`. The generated
iterator compares `TimelineHandle.data.cutsceneName` against that allowlist and
calls `_PreBindAnimationOutput`; it is cinematic compilation context, not
mission dispatch. Fifty-six strings have authored-name Story transforms, 54
also have typed `timeline_targets_story` containment, and 53 were already
mission-connected by stronger evidence. The three residual Story files
(`dlg_e11m5_9`, `dlg_e11m8_9`, `dlg_e5m0d5_1`) have exact Timeline and
PlayableDirector parents but no typed mission/quest/level/LevelScript owner.
The IFix allowlist therefore proves zero new pipeline bindings; do not convert
`dlgtl_`/`dlg_` naming into a mission shell.

The current native narrative-black queue path is also closed as an ownership
source. `NarrativeBlackScreenAction`, its complex/teleport variants, and
`NarrativeBlackScreenQueueItemData` carry mask/audio/text/fade data but no
mission id. `GameAction.ShowNarrativeBlackScreen` writes only the passed
`UICommonMaskData` pointer at queue-item `+0x48`; the base `cinematicId` is not
authored on this path, and `ShowNarrativeBlackScreenByHandle` only reads the
handle back before showing the mask. The current Persistent IFix payload does
not target either method, so the installed fallback bodies are authoritative.
Queue ids, handles, and callbacks therefore remain local presentation state,
not a Story-to-mission bridge.

LevelScript synchronization is likewise runtime state, not mission ownership.
The installed client sends
`CS_SCENE_SET_LEVEL_SCRIPT_ACTIVE {sceneNumId, scriptId, isActive, leaderPos}`
and `CS_SCENE_SET_LEVEL_SCRIPT_START {sceneNumId, scriptId, isStart,
leaderPos}`; asynchronous server pushes report the same scene/script identity,
state/stage, and completion flags. These packets contain no MissionRuntime,
quest, Story, or black-line id. The teleport-coupled black action uses the
normal `CS_SCENE_TELEPORT` / `SC_SCENE_TELEPORT` / finish-ack lifecycle, which
also carries no mission/quest ownership field.

The client-side teleport carrier does not restore that missing ownership.
`Beyond.Gameplay.TeleportParam` is a 0x38-byte value with `missionId` at
`+0x18`, `levelScriptId` at `+0x20`, `actionId` at `+0x28`, and `performId` at
`+0x30`, making it the sole new actionable result in a whole-metadata 20-type
nominal mission/script co-carrier census. Exact current direct callers show
that its producers either zero the entire value or set only
source/UI/options/reset/callback state. `LoadingPipeline.LoadFinishStep` reads
source/script/action for the local teleport-finish LevelScript event or
callback identity for the callback lane, while `PerformerFactory` reads
`performId`; none of the audited consumers reads `missionId`. The current
30-target Gameplay IFix payload replaces none of those methods. This field is
therefore unused on the audited current fallback path, not a mission-to-script
edge. Future patch, indirect, reflection, or XLua construction remains outside
the bounded negative.

The installed binary also separates a client LevelScript request from an
independent server-pushed client event. `GameplayNetwork` sends
`CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER {sceneNumId, scriptId, eventName,
properties, ctxToken}` and receives the fieldless
`SC_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER` acknowledgement. Separately,
`GameplayNetwork._Handle_SceneTriggerClientLevelScriptEvent` at `0x187386320`
consumes `SC_SCENE_TRIGGER_CLIENT_LEVEL_SCRIPT_EVENT {sceneNumId, scriptId,
eventName, ctxToken}`, constructs the exact script receiver, and calls
`LevelEventManager.RaiseScriptEvent` at `0x186f922a4`. The handler allocates
`EventParams`, sets its receiver to `LevelScriptPtr(scriptId)`, and, when the
protobuf `ctxToken` bytes are non-empty, stores them in the inherited parameter
blackboard before dispatch. The token is therefore opaque propagated event
context rather than an ignored field. Its static ParamBlackboard key lives at
`0x18e2eef08`; a whole-binary direct RIP-reference census finds four references
in exactly the handler and `Beyond.Gameplay.Actions.CallServer.Execute`.
CallServer's generic-shared `TryGetValue` call reads the value as `netToken`,
then `GameAction.TriggerServerEvent` and
`GameplayNetwork.TriggerLevelScriptServerEvent` pass it to
`CS_SCENE_LEVEL_SCRIPT_EVENT_TRIGGER.set_CtxToken`. The current installed
30-target Gameplay IFix payload targets none of these methods. This closes the
current direct AOT lane as server-event round-trip/correlation context, not a
mission or quest id. Neither message carries a mission, quest, condition, or
Story id. The server push is therefore exact runtime causality but not a
pipeline ownership edge; event-name equality or token presence alone must
remain unpromoted. Separately constructed equal keys, reflection, native
memory manipulation, future patches, and future builds remain outside this
bounded result.

The generated protobuf surface has now been checked recursively rather than by
top-level field names alone. Resolving every field through the installed
MetadataRegistration runtime type table covers 983 enum-backed CS/SC message
classes and nested `Proto.*` fields. The census finds 33 mission/quest-bearing
messages, 29 `scriptId`-bearing messages, and zero message co-carrying
mission/quest identity with a LevelScript or Story identity. The only weaker
mission/scene carriers are `CS_MISSION_CLIENT_TRIGGER_DONE` (317), whose
current fallback sender is absent, and the nested
`roleBaseInfo.sceneName` fields in `SC_MISSION_STATE_UPDATE` (112) and
`SC_QUEST_STATE_UPDATE` (111). Identity normalization explicitly excludes
`requestId`/`soilRequestId` from quest classification, strips `transcriptId`
before script classification, and treats `cutsceneId` as Story rather than a
generic scene host; focused regressions pin those boundaries.

Native decoding closes the active pair as operational state. Both handlers
read `roleBaseInfo.leaderPosition`, `leaderRotation`, and `sceneName` and call
`MissionSystem.CharacterPositionCorrection` at `0x1873b84c4`. That consumer
resolves the scene to a map and performs guarded player/squad position
reconciliation; it does not retain an authored mission/quest scene host or
address a LevelScript/Story record. The installed 30-target Gameplay IFix
matches none of the handlers or consumer. The result adds no graph edge and
must remain bounded to typed current-client schemas; opaque bytes, dynamic
parameters, server-only data, native construction, and future builds remain
outside it.

The remaining exact managed-carrier queue also closes
`Beyond.Gameplay.MissionOptionData`. Metadata proves `missionId` at `+0x68`,
`callDialogId` at `+0x70`, and handler enum value 3 (`Mission`).
`MissionOptionHandler._DoAction` at `0x186e510a4` does not consume those fields
as a pair: a non-empty `callDialogId` calls `StopAndPlayDialogById` and jumps to
the end, while `AcceptMission(missionId)` is reachable only through the
empty-dialog branch. The record shape is therefore an alternate-action union
in practice, not a mission/dialog bridge.

The source boundary is complete for current exported surfaces: 1,325,026
MonoBehaviour object-index rows, 8,195 decoded TextAsset payloads, 179,925
structured JsonData files, and 1,291 installed Lua files contain zero exact
`MissionOptionData`/`callDialogId` occurrence. Whole-binary direct calls add no
constructor/getter producer, and current IFix replaces none of the four pinned
methods. The hash-pinned rerunnable report is
`reports/story/recovery/mission_option_carrier_audit.{json,md}`. This result
adds zero ownership/order edges and should not be repeated until the binary,
metadata, exported data, or IFix changes.

The superficially stronger nested managed-type join through mission properties
is also a false foreign key. `MissionRuntimeAsset` serializes
`List<ParamKeyValue> properties` at `+0xe0` and allocates a separate empty
`Dictionary<string, ParamVariable> propertyDic` at `+0xf8`.
`MissionSystem.MissionData.propertyDict` is another dictionary at `+0x20`.
Although the shared `ParamVariable` type has `m_scriptPtr` at `+0x70`, current
authored `properties` rows contain only the ParamKeyValue/value scalar shape,
not a script pointer: 217 rows across 71 of 490 mission assets, with zero
`scriptId`/`LevelScriptPtr` nested fields.

Native construction keeps the two contexts separate. Sync-all, incremental
mission-property update, and mission-state update each call
`ParamVariableExtensions.ToVariable(Proto.DYNAMIC_PARAMETER)` and write
`MissionData.propertyDict`. A complete direct-call census finds zero
MissionSystem call to either LevelScript setup method. The mapped setters of
`m_scriptPtr` are property/blackboard event registration paths owned by
`LevelEventManager` and LevelScript `ScriptEvent` receivers. One BB setter
callsite remains native/generic without a managed owner, but its call shape has
only a LevelScript pointer/key and no mission identity. The installed IFix
matches none of the reviewed paths. The maintained fail-closed report is
`reports/story/recovery/mission_property_scriptptr_audit.{json,md}`; its
classification is `runtime_context_only_no_mission_levelscript_edge` and it
adds zero bindings.

The action-context form of the same proposed bridge is now closed separately.
Current metadata proves `ParamSource.CURRENT_MISSION_ID=1004` and
`Param<T>.get_isCurrentMissionId`, so an authored action can request its
mission identity without serializing a literal string. The exact current
corpus uses that feature only 18 times across six of 490 MissionRuntime assets:
17 `CheckMissionIntProperty` inputs and one `CheckMissionBoolProperty` input,
all referring back to the already-owned current mission. None supplies a Story
id.

No LevelScript uses the feature. A complete scan of 4,512 raw LevelScript
files / 74,839 UID records finds zero little-endian 1004 values, zero validated
Param tails with source 1004, and zero embedded JSON parameter objects with
that source. The installed IFix target list adds no reviewed context method.
The maintained report is
`reports/story/recovery/param_source_mission_context_audit.{json,md}`; it adds
zero mission-to-script, Story, quest, or order edges and fails closed on
binary, metadata, authored-count, action-type, or IFix drift.

The complete direct managed-field carrier surface is now enumerated too.
Across all 63,987 current metadata types, ten types directly pair a
mission/quest identity field with a LevelScript/scene or Story identity field.
Two are schema vocabularies rather than value carriers
(`IdPickerAttribute.StringIdType` and `PropertyKeys`). The eight object types
are `CommonTrackingPointInfoBase`, `FocusModeInstanceData`,
`NpcRuntimeProxyExData`, `SubGameInstanceData`, `MissionOptionData`,
`TeleportParam`, `TrackingInfoBase`, and
`CS_MISSION_CLIENT_TRIGGER_DONE`; all eight now have bounded verdicts.

FocusMode, NpcProxyEx, and SubGame are the already recovered productive
classes, with 13 mission/radio rows, 453 mission/dialog rows, and 20
mission/bound-script rows respectively. Their semantics remain bounded context
or runtime shells. The newly decoded tracking pair is not activation:
`CommonTrackingSystem.AddMissionTrack` stores mission identity on a tracking
point, `_UpdateVisible` uses `sceneId` only to compare system maps, and
`TrackingInfoBase` adds/removes the tracker key. There is no Story call and no
current IFix replacement.

The hash-pinned report
`reports/story/recovery/managed_identity_carrier_census.{json,md}` therefore
records ten direct candidates, eight object candidates, zero unreviewed
candidates, and zero new graph edges. This closes direct named-field searches;
nested object graphs, indirect construction, opaque server state, and
unexported asset kinds remain distinct frontiers.

The nested managed-type frontier is now resolved independently of DummyDll
quality through `Il2CppMetadataRegistration.types`. Runtime type decoding
recovers generic collection arguments and custom object dependencies, and a
depth-three traversal over 63,208 unique definitions produces 25 exact
candidate roots: 11 direct-exact and 14 nested-dependent. Every candidate is
classified, with zero unreviewed rows. Most nested hits are global aggregate
objects whose independent caches must not be joined; the positive-looking
rows are already recovered AirWall/FocusMode/NpcProxy/SubGame/DomainDepot/
RadioTriggerZone contexts.

The last binary/Lua check bounds the only otherwise novel small path.
`DialogManager.m_pendingItemSubmitter` is at `+0x200`, while
`InventoryItemSubmitter.questId` is at `+0x20`.
`CinematicSystem.SendFinishDialog` is the sole direct
`TryGetSubmitMsg` caller, but there are zero whole-binary direct callers of
both the submitter constructor and `RegisterPendingSubmission`, and current
IFix targets none of them. This is not an inactive producer: a hash-pinned
targeted VFS dump proves shipped `SubmitItemCtrl.lua` constructs and registers
the object through XLua. `DialogOpenUIPanel` is directly called by both
`DialogManager.OpenUI` and the generated XLua wrapper. The typed authored
surface contains 13 SubmitItem OpenUI terminals, but only three stock
placeholder parameter objects, ten empty params, and zero concrete quest ids.
The fallback does not synthesize the absent id:
`DialogTreeOpenUINode.DoAction -> DialogManager.OpenUI ->
GameAction.DialogOpenUIPanel` forwards the original action and parameter
string, while hash-pinned shipped `PhaseDialog.lua` JSON-decodes that string
and adds only `fromDialog` and `actionData`.

The authored mission surface nevertheless contains three exact
`CheckQuestSubmitItem` objective conditions across three quests/missions. All
three submission ids resolve to `SubmitItem.json` item/count requirements.
Two share the same authored AND objective with `CheckTalkOptionFinish`, but
their dialog ids overlap none of the 13 SubmitItem OpenUI terminals. These
relations are emitted as quest-to-submission requirements and bounded dialog
co-gates, never as quest-to-OpenUI ownership or mission order.
One separate objective, `sm2l7m1_q#17`, has an exact authored AND between
`submit_item_sm2l7m1` and
`CheckLevelScriptStageReachMax(map02_lv008/23100170008)`. The submission row
requires one `item_mission_sm2l7m1_flute`. The LevelScript independently has
an exact `LevelEvent_OnDialogExit(dlg_sm2l7m1_17)` path whose typed
`StartDialogAndTeleportAction` target is `dlg_sm2l7m1_9`, plus a separate
Leader-enter path to the same target. The raw `0x09b9/0x00` record at the
other dialog-exit root and the matching records late in both playback chains
are compact MemoryPack tag `0x00b9` with nine members. Installed ActionBase
formatter registration (`mov r8d,0xb9`, metadata type index 125956) names the
class `ExitLevelCustomPerformance`; each target-script instance has the exact
same 17-byte, string-free payload containing only an unbound zero
`Param<uint>` handle. The neighboring formatter tags close both playback
chains end to end: `0x04ca/0x09` is
`ToggleClearScreenButRadio(_isShow)`, first `false` and later `true`;
`0x02fe/0x0a` is `MainCharMoveTo(_endPos,_groundedMoveGait)`, with
`_endPos` bound through param source 200 to `walk_end_pos` and gait 0. Both
generated setter names and exact EOF payload decodes agree. Finally, raw
`0x0e34/0x00` normalizes to ActionBase tag `0x0034`/14 members
`CallServer`. Its generated six fields decode as null client-output UIDs,
`event_args`, an event name, `useCustomEvent=false`,
`waitForCallback=true`, and `withEventArgs=false`; no mission or quest
identity is serialized in that server handoff. Across the complete current
typed corpus, every hash-shaped event name equals `#` plus the same
CallServer action-record UID. This closes the value as an action-local
callback/correlation label rather than a handler hash, Story node, mission
owner, or chronology edge. The Story builder now preserves it only as a
diagnostic callback record and excludes it from scene-graph nodes and edges.
The adjacent graph audit also found one distinct punctuation-only `#` string
in `PlayDialogAndHideSceneObjectAction` `0x035a/0x0f` (record UID
`15196cb4`, `map02_lv005/23200050003`) beside the actual dialog id. It is
retained as a typed non-node scalar diagnostic and does not become an
identifier or edge.
The script therefore contains
no hidden submission id, item id, UI key, branch target, or typed SubmitItem
OpenUI action. Mission Pipeline schema 14 emits one
LevelScript co-gate and the source graph joins the quest, submission, script,
dialog-exit trigger, and playback target while marking every context edge
`openUiOwnership=false` and `orderEvidence=false`.
The hash-pinned report
`reports/story/recovery/nested_managed_identity_carrier_census.{json,md}`
therefore adds no Story ownership/order edge and fails closed if the candidate
set, callers, binary, metadata, either Lua file, authored MissionRuntime/
SubmitItem/OpenUI census, or patch changes.

The non-protobuf runtime-type census found one complete serialized carrier in
`Beyond.Gameplay.LevelData.airWalls`. The current LevelData MemoryPack root has
43 members and `airWalls` is member 0. Generated wrapper setters prove the
alphabetical `AirWallGroup` order:
`bounds/checkData/defaultOn/groupId/polyLineWalls/pushBackRadioId/scriptId/slotId`.
The nested check schema is likewise exact:
`AirWallCheckData(checkType, missionData)`,
`MissionTotalCheckData(downReason, isDownAny, isRiseAny, riseReason)`, and
`MissionCheckData(detailState, id, isQuest, isSame)`.

The maintained guarded parser validates every object member count, collection
frame, UTF-8 string, boolean, and nested boundary. It decodes 822 groups from
228 of 958 LevelData files with zero failures. There are 211 mission-checked
groups, 78 radio groups, and 60 groups carrying both. Exact current
MissionRuntime/quest and Story lookups retain 58 radio contexts; two mixed
`e7m3` groups are rejected because quest-looking ids are authored with
`isQuest=false`. This is a useful fail-closed model for future non-protobuf
carrier work: accept typed discriminator semantics, not identifier spelling.

Native consumers give the fields their bounded operational meaning.
`AirWallManager` indexes groups by cared mission/quest id and listens for the
synchronized state changes; `AirWallGroupAgent` re-evaluates the predicates.
`TriggerMainCharGoBack` later reads `pushBackRadioId`, and its callback calls
`GameAction.PlayRadio`. The carrier therefore creates an exact local
state-gated playback context. It does not make state transition equal playback,
and it creates no Story ownership or mission-order edge. The current installed
30-target Gameplay IFix replaces no AirWall method.

GameAssembly metadata names server-action families such as
`TriggerLevelScriptCustomEvent`, `TriggerClientLevelScriptEvent`,
`SetLevelScriptEnabled`, and `UpdateLevelScriptProperty`, but type names alone
are not serialized instances. Across the current 980 exported
MissionRuntimeAsset files, `actionMapRaw` exposes 546 client actions and only
six concrete action types (PlayRadio 366, ShowLimitedGuide 81,
ManuallyStartGuideGroup 65, ShowChapterCompletedPanel 17,
ManuallyAcceptClientGuideGroup 16, ShowChapterPanelWaitForFinish 1). It exposes
no serialized LevelScript/server-action operand that can join a mission to a
script. Recovering an original server policy/config or activation registry is
therefore the next distinct ownership surface; the enum catalog is not a
binding source.

One exact original-data activation registry is now decoded, with a deliberately
narrow scope. `GameplayConfig/SubGameInstanceDataTable.json` contains 469 typed
rows; 20 rows carry `id`, UInt64 `bindScriptId`, and nonempty
`dungeonMissionId` together, yielding 20 conflict-free mission-to-bound-script
pairs. The installed MemoryPack setter proves the script field is UInt64.
`SubGameManager.SrvCreateSubGame` at `0x1870b31c8` passes the synchronized
subgame identity through `GameModeFactory.CreateGame` at `0x186f55a38`, which
resolves the typed table and constructs the concrete dungeon/week-raid runtime.
This is exact mission-shell runtime context, not a quest or Story playback edge.

The packet and native boundary is now exact. Client GameMechanics lifecycle
requests carry `gameId`; `SC_GAME_MECHANICS_SYNC_ENTER_GAME_INST` returns
`gameId`, `gameInstId`, `gameUniqueId`, and `isReenter`. The enter handler at
`0x18736b59c` passes `gameId` through the factory lookup, while the instance ids
remain live-runtime identities. None of the audited lifecycle packets carries
`missionId`, `questId`, `sceneNumId`, or `bindScriptId`. Start parameters contain
only start/expiry timestamps and completion parameters contain only pass time.

The installed MemoryPack setter at `0x18a145de8` writes `bindScriptId` to exact
row offset `+0x50`. The shared SubGame base stores that typed row at runtime
offset `this+0x60`. `WorldChallengeGame.SendQuit` at `0x186f60cc8` reads the
same field, constructs a `LevelScriptPtr`, resolves it through
`LevelScriptManager.TryGetLevelScript`, calls `LevelScriptRuntime.ManualEnd`
when the script type is not 5, and then sends `CS_GAME_MECHANICS_REQ_STOP`.
This proves an operational lifecycle/cleanup association. The audited concrete
`DungeonGame`/`WorldChallengeGame` start bodies and shared `BaseSubGame<T>`
start body do not read `bindScriptId`; no start/enable consumer was recovered in
that bounded runtime audit. Do not describe the field as proven activation.

All 20 bound script ids are unique validated LevelData member-22 roots, but all
have `parentLevelScriptId=0`; their 20 LevelData shells contain no direct or
transitive script descendants. None intersects the 182 unresolved native-
playback Story files. The only positive playback control is already connected
independently, and seven other SubGame/playback intersections have no
`dungeonMissionId` or other mission owner. Therefore this registry adds zero
Story bindings, and neither same-level siblings nor filename families may
inherit its mission. The next useful binary surface must co-carry or resolve a
full scene/script address and an authored mission/quest owner; the proven quit
consumer alone cannot provide either missing identity.

Those ten missionless intersections are now represented rather than hidden.
The coverage builder joins each missionless row's exact `bindScriptId` to the
same script id on a decoded native playback occurrence, yielding ten runtime
nodes, nine unique Story files, and fourteen SubGame-to-Story placements. Four
boss-rush rows share `cutscene_e1m8_2`, three share
`cutscene_e3m5_1`, and the three WorldChallenge rows cover seven activity Story
files. These remain outside connected-mission coverage. The strongest
original-data owner candidates were also exhausted. Boss-rush
`dung01_bossrush01_01` has a `QuestStateEqual(e1m8_q#4)` unlock prerequisite,
while `dung01_bossrush03_01` has the adjacent enum value
`MissionStateEqual(e3m5)`. The latter's exact node reaches
`bindScriptId=17500000002 -> cutscene_e3m5_1`, but the mission state gates only
SubGame availability; it does not own or trigger playback. Activity stage 6
co-identifies `missionId=a1m6d6` and
`rankRelatedId=activity_qingxi_qiangti_6`, but native runtime storage keeps
stage mission state separate from rank-related game-mechanic info. Stages 3/4
have blank `rankRelatedId`. All ten target scripts are parent-zero roots with
one MainTask, no mission/quest literal, and no exact MissionRuntime occurrence.

`DungeonTable.sceneId` now supplies a broader, still non-owning host join for
the unresolved native receiver frontier. Eighteen receiver scripts carrying
fourteen Story keys live on six exact scenes used by typed SubGame rows,
producing forty receiver/SubGame context placements. Seven placements are the
SubGame's exact `bindScriptId`; thirty-three are other LevelScripts in the same
scene and are explicitly labeled siblings. The attached condition rows produce
thirty-one availability annotations, not owner edges. The strongest negative
control is `dung02_bdg002/41100000004 -> cutscene_e9m3_2`: its same-scene
first-tier boss rush is unlocked by `QuestStateEqual(e9m4_q#1)`. This
cross-named current-build row demonstrates that even an exact dungeon scene
plus quest/mission prerequisite cannot be promoted to Story ownership,
activation, or order.

The typed SubGame payload further sharpens three raid scenes without changing
that result. `DungeonSubGameData.dungeonMissionId` supplies nine exact
receiver-scene mission-shell contexts covering ten Story keys, but all nine
receivers differ from the row's `bindScriptId`. The shipped rows disprove
sibling inheritance: `dung_wolfgd_01` carries `c6m3` while its sibling scripts
play `c6m1` Story, and `dung_aglina_01` carries `c13m2d5` while its siblings
play `c13m2` Story. `dung_kamiu_01`'s `c33m2` name agreement is therefore not
admissible ownership evidence. Keep `dungeonMissionId` as typed SubGame
mission-shell context unless the receiver itself is the bound script or a
separate exact control edge connects the two.

The remaining serialized SubGame whitelist fields are now census-closed as an
ownership route. Across all 469 typed rows, `missionWhitelist` and
`logicIdWhitelist` are always empty. Exactly one row,
`f1m18d1_1`, carries a `proxyWhitelist` (three proxy ids). Those proxies resolve
to two nonempty NpcProxyEx dialogs, `dlg_f1m18d1_4` and
`dlg_f1m18d1_8`, and every NpcProxyEx `missionId` on the three rows is blank.
Both dialogs already have stronger exact evidence: q4 checks completion of
`dlg_f1m18d1_4`, while the bound LevelScript contains the native
`dlg_f1m18d1_8` playback. The third proxy has no dialog. Whatever additional
runtime filtering the whitelist performs, the complete shipped instance
surface contributes zero new unlinked Story owner, quest placement, or order
edge.

The DungeonSubGame death-presentation tail is also exhausted for Story
recovery. All 250 typed Dungeon rows have an empty
`conditionalDeathPerformanceEntries` collection. Sixteen enable
`useTeamDieBlackscreen`, but their only nonempty hint is the shared localization
key `dungeon_blackscreen_text`; no row serializes a `black_*`, dialog, radio,
cutscene, mission-option, or LevelScript action id in these fields. They prove
generic team-death presentation policy only and cannot attach any unassigned
black Story file to the row's otherwise exact `dungeonMissionId`.

The companion installed-VFS scan also closes the server-action-enum shortcut.
Across 90,659 JsonData/Table candidates, 532 structured files were schema-
checked for action ids 2013, 4003, 5106, and 5212. Sixteen scalar matches were
unrelated table ordinals, priorities, chain ids, or map marks; zero occurred
under a server-action/action-map field. The native enum values prove protocol
capability only, not shipped instance ownership.

Server objective progress arrives through `SC_QUEST_OBJECTIVES_UPDATE`
(message 116): `questId` plus
`questObjectives[{conditionId, extraDetails, values, isComplete,
descriptionIndex}]`. `MissionSystem.Handle_QuestObjectiveUpdate` at
`0x183a882e0` first resolves the exact quest and then refreshes its objective;
the safe identity is therefore `(questId, conditionId)`, never `conditionId`
alone. This matters in the current original corpus: 1,932 direct placeholders
cover 1,930 quests in 377 missions but only 1,843 distinct condition ids; 17
ids are reused across 106 rows, with one value appearing 59 times. There are no
nested placeholder instances, and only `sm2l4m1_q#4` contains more than one
(three). The packet contains no scene, LevelScript, entity, trigger, spawner,
or Story key, while the corresponding LevelScript protocols contain no
`questId` or `conditionId`; it is not a Story attachment bridge.

The exact residual-corpus audit reinforces that boundary. All 182 currently
unassigned native Story keys, organized under 210 exact receiver-to-Story
placements with zero missing runtime selectors, were checked
against placeholder actions, tracked scripts/entities and save properties,
entity suffixes, mission-area geometry, positions, SpawnerConfig, raw
condition-id bytes, and NPC proxies. None supplies a safe join. Of all
placeholder rows, 159 carry client actions and 139 have exact Story references;
those 139 references were already connected by their authored action data, so
the placeholder itself promotes zero additional Story files.

Current LevelScript branch wrappers are exact enough for diagnostic native
Story paths. `Split` serializes a u32 count plus that many signed local action
ids. `IfElseAction` serializes its condition, false action id, then true action
id; runtime execution schedules the common base `nextId` first and then the
selected branch. Static traversal therefore retains `nextId` and both typed
branch ids. Duplicate local ids are accepted only when every serialized record
has the same typed tag/member count, text operands, `nextId`, and decoded branch
targets; all equivalent offsets are retained. Conflicting duplicates still
fail closed. The current ActionBase table also identifies
`PreloadCutsceneAction` (`0x0376/0x0c`), `RaiseCustomLevelEvent`
(`0x037e/0x0a`), `RaiseCustomScriptEvent` (`0x0380/0x0b`), and
`WaitForNpcProxyReady` (`0x04f5/0x09`). Traversal never converts an event or
trigger slot into mission ownership by itself.

The corresponding PureGetter union now has an exact mission-state path.
`GetMissionState` is tag/member `0x013a/8` with one constant
`Param<string> _missionId`; `CompareMissionState` is `0x001f/10` with
`Param<BoolComparer>`, a referenced mission-state getter, and a constant
`MissionState`. Installed metadata and native bodies prove `Equal=0`,
`NotEqual=1`, and `MissionState.Completed=3`. The exact IfElse branch edge is
therefore a direct mission-to-Story state dependency, including completed
prerequisites in nested paths; it is not a quest owner. `GetResult` reads
`GameInstance.player.MissionSystem.GetMissionData(...).state` locally and sends
nothing. `SC_SYNC_ALL_MISSION` and `SC_MISSION_STATE_UPDATE` are independent
upstream pushes that populate the cache, not responses to the getter. These
method semantics describe the installed native fallback and retain an IFix
re-audit caveat. Only the single-mission `Equal(Processing)` true branch is
narrow enough for weak mission-shell playback context; the other exact state
edges remain non-owning dependencies.
`RaiseCustomScriptEvent` has 11 serialized members. Its exact current payload
is an 18-byte event-arguments parameter, one tagged event-key parameter and
12-byte parameter tail, followed by a 29-byte four-member
`Param<LevelScriptPtr>`. Receiver `ParamSource=1002` is
`CURRENT_SCRIPT_ID`; the constant form carries one explicit uint64 script id.
The maintained decoder fails closed on dynamic receiver shapes. Across all
typed Story listeners it currently recovers 46 producer records for 40 Story
files; 15 routes appear on 10 still-unassigned pipeline rows. This is exact
local producer/listener causality, not mission ownership or a server exchange.
ActionBase tag/member `0x0365/0x11` is now exact `PlayRemoteComm`. It exposes
`remotecomm_e11m1_1` at `map02_lv007/10200060020` through a Leader-enter
slot-80002 header and attaches it only because that playback script has a
separate validated `e11m1` LevelData host. It also exposes the still-unassigned
`remotecomm_e3m1_2` route at `map01_lv007/2800010027`, where Leader-enter slot
80001 starts `dlg_e3m1_1d5` and then the remote communication; the event path
alone does not choose a mission.
`SwitchInt` is now exact for current tag/member `0x04bd/0x0c`: it serializes a
u32 case-id count plus signed local ids, a u32 case-value count plus signed
values, one signed default id, and a typed PureGetter value tail. All 820
current records decode with equal list lengths; 1,704 positive case targets and
the one positive default target resolve, while `-1` case and `0` default
sentinels remain non-edges. This restores exact event-owner paths for the 12
playback keys that previously stopped before a branch.

The current branch-predicate surface is also typed by PureGetter union tag and
member count. Exact operand readers cover `BooleanCompare` (`0x0004/10`),
`FloatNewCompare` (`0x0049/10`), `GetLevelScriptPropertyGenericBool`
(`0x0100/9`), `GetLevelScriptStage` (`0x012f/8`), `GetterInt`
(`0x0184/8`), `IntCompare` (`0x01aa/10`), `IntEqual` (`0x01ac/9`),
`IntGetterRandom` (`0x01ba/9`), and `IsEndminGender` (`0x01c2/8`). They decode
the authored Param source/path/value tails, comparer enum, referenced local
getter, LevelScript target, or gender enum and accept only exact subtype EOF or
one explicit outer ActionMap u32 trailer. The same union map names
`GetConditionResult` (`0x004e/8`); those branches remain structurally
traversable, but its delegate-backed inner condition object is a
bounded semantic stop. Number comparers use `Equal=0`, `NotEqual=1`,
`GreaterThan=2`, `GreaterEqual=3`, `LessThan=4`, and `LessEqual=5`; bool
comparers use `Equal=0` and `NotEqual=1`.
`IntGetterRandomForMemoryPack` serializes `_max` before `_min`; the decoder
preserves that generated setter order while publishing normalized
`minimum`/`maximum` fields.

The current event decoder now also covers every selector used by the 71
Story-bearing native branch groups. `ParamOutput` retains source-100/null-path
outputs without relabeling them as local property refs; `EntityEventHeader`
accepts an authored validation getter reference such as id `5`, source `-1`;
zero-field `ScriptEvent_OnScriptComplete` is decoded from its exact inherited
prefix even when outer ActionMap bytes follow; and
`LevelEvent_OnSpawnerEntityDie/Start/End` follows the generated setter order
entity output, filter type, group filter/output, spawner filter, and wave
filter/output. The e11m3 current instance decodes an exact constant spawner id
`23100080001`, null group/wave filters, and all three output refs. These fields
describe the local runtime receiver only and introduce no mission foreign key.

`Play3DRadio` is exact for tag/member `0x034a/0x14` when its 12-field payload
consumes the record to EOF. The setter order is attenuation type, advanced
options, entity pointer, from-begin, index, no-flush, NPC proxy id, only-once,
radio id, reverb offset, use-NPC-proxy, and voice offset. Native execution
resolves a true `useNpcProxy` through `NpcProxyMgr` and calls
`PlayRadioOnEntity`, so the proxy is the actual emitter target. Of 173 current
field schemas, 159 have the exact EOF-bounded outer form; nonempty proxy text
alone is never sufficient because 11 records carry it while the flag is false.
For headerList envelopes, the fixed signed field at record start `+26` is
`ActionHeader.filterLevel`, not an action edge; the derived payload stores
`filterMask` at `+0` and the actual `ActionHeader.nextID` at `+5`. Current rows
prove these values can differ. A fail-closed 84-byte
`LevelEvent_OnEntityHpChanged` reader also recovers the e11 event as direction
`Down`, entity slot `40021`, and HP ratio `0.1`; this explains the local event
condition but supplies no mission owner.

`WorldEntityRegistry.npcProxyBriefInfos` provides a different, weaker exact
identity. Its dictionary key must equal the row's positive-u64
`segmentIdGlobal`; when that value also equals a same-scene Story-playing
LevelScript global id, typed MissionRuntime `NpcProxyTrackingInfo.proxyId` and
agreeing nonempty `NpcProxyEx.missionId` rows can scope the authored segment to
one mission shell. Every raw/native occurrence normalized to the Story output
must resolve through the same mission, or the join fails closed. The current
census has nine direct normalized outputs; native-black and four
`dlg -> misc_dlg` aliases explain why an earlier raw-key-only audit saw four.
This is not a runtime activation chain. `NpcProxyTrackingInfo.GetTargetPos`
passes only `proxyId` to `NpcProxyMgr.TryGetProxyByProxyId` and reads AOI
position; it does not consume `segmentIdGlobal` or call the registry. The only
recovered direct native caller of the registry proxy lookup serves a DomainDepot
position path, not a LevelScript loader. The relation therefore stays
`derived_exact_shell`, with no quest/NPC causality and no server exchange.
Three remaining trigger-volume Story files have the weaker numeric coincidence
without the typed MissionRuntime tracking carrier:
`dlg_e3m2_2` shares script/segment `2800010011` with an `e3m4` proxy, while
`dlg_e3m3_8` and `radio_e3m3_4` share `2800010014` with an `e3m5` proxy. They
remain unbound. No recovered native consumer interprets `segmentIdGlobal` as a
LevelScript id, and proxy-table mission ownership alone cannot transfer to every
action in a numerically equal script.

The HP decoder now also accepts the exact current dynamic-list shape. It keeps
the LevelScript property source/path, direction, threshold, and null output.
One fail-closed same-script producer join requires exactly one
`OnSpawnerEntitySpawn -> ListAddValueEntityPtr -> named list` chain with a
constant spawner/group and matching `$<header>@_entityOutput` reference. The
same-level SpawnerConfig mission-token rule then recovers exactly
`radio_gm02m20_9` and `radio_gm02m20_18` as `gm02m20` mission context via
spawner `23100270003`, group `101`, list `entity03_01`, and a 1% downward HP
threshold. HP dispatch is local and the mission objectives are server
placeholders, so both remain mission-shell context with no quest binding or
request/response edge. The equivalent e11 `tiger` producer uses spawner
`10200260005` but its config has no authored mission token; five e11 files stay
unowned.

The inherited `ScriptEventHeader` layout is now replayed in setter order after
the variable-length `ActionHeader._validate: Param<bool>` field. This matters
because values such as `10`, `45`, and `122` in that prefix are validation-node
`idRef` values, not script ids. `_targetScript: Param<LevelScriptPtr>` follows
the validate object, then `_triggerTarget` (`SELF=0`, `SPECIFY_SCRIPT=1`). A
specified pointer can serialize a `scriptId:uint64` but never a mission/quest
id. All 1,052 current `OnScriptActive` and 455 `OnScriptStageChanged` headers
use `SELF` with null `_targetScript`. Active has no subtype fields; StageChanged
adds `_newStageFilter: Param<int>` and `_newStageOutput: ParamOutput<int>`.
Both headers receive local `LevelScriptRuntime` events, but StageChanged has a
now-proven upstream server route. One-way
`SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE {sceneNumId, scriptId, stage}` reaches
`GameplayNetwork._Handle_SyncLevelScriptStage` at `0x1873867cc`, resolves the
exact ready runtime, calls `LevelScriptRuntime.UpdateStage` at `0x186fad930`,
then raises the local SELF-scoped event. Current metadata has no corresponding
client request and this route expects no response; the packet still carries no
mission or quest id.

The residual Story ownership audits now close both lifecycle/trigger families
more tightly. The original 18-file `OnScriptStageChanged` family has 21 exact
playback occurrences across 14 owning LevelScripts; all 980 current
MissionRuntime assets contain zero whole-token references to those script ids,
the source graph has zero mission/quest/condition incident edges, and LevelData
member-22 yields no mission host for any pair. The original 74-file
`OnLeaderEnterTriggerVolume` family has 78 exact playback occurrences, 60 exact
receiver nodes, and 53 unique level/script owners across 13 levels. Its
receiver serializes only `_triggerSlotIdFilter` and `_triggerSlotIdOutput`, and
native `Process` consumes the local trigger-slot event before delegating through
`ScriptEventHeader`. MissionRuntime has zero exact target-script carrier
intersections, all 53 `LevelScriptBriefData.parentLevelScriptId` values are
zero, and the three exact MissionArea host pairs are shared by both `c13m2` and
`c13m2d5`; there are zero unique hosts. Three target scripts are the
already-exposed missionless activity SubGame nodes covering seven Story files;
their rows carry no mission owner. All 60 matched trigger volumes have
`waitSrvRes=false`. The parallel touch request/response carries scene, script,
local slot, and enter/leave identity but no mission or quest id, so the event
and packet alone cannot promote a mission-owned Story attachment.

A separate exact current-build foreign-key route now recovers two quest/script
contexts and three Story files from that Leader family. Native
`CheckMonsterKilled` stores its typed WorldEntity list at `+0x98`; the complete
three-entity set in `e3m2_q#3` exactly equals LevelScript `2800010045`'s
`LevelScriptBriefData.refWorldEntityIdList`, and the script's exact Leader-enter
path plays `radio_e3m2_7`. Native `InteractiveCheckInt` stores one
`EntityPtr` at `+0x90`; the three direct children of `gm02m11_q#4`'s
`CombineCondition` are a unique subset of script `22800330000`'s five BriefData
WorldEntity references, and its exact path plays `black_gm02m11_1` before
`cutscene_gm02m11_Activate`. `EntityPtr.useSlotId=false` resolves `logicId`
through `WorldEntityRegistry`, not the script-slot namespace. All six entity
ids are unique to their one canonical MissionRuntime quest and all same-level
BriefData occurrences agree. This is a shared authored entity context only;
the recovered schemas do not prove a quest-to-trigger call or paired server
exchange. The remaining Leader-family queue is 71 Story files.

The same foreign-key rule now closes three more pipeline-relevant Story files
and three level-owned cutscene Story assets. `e2m5_q#15`'s complete five-enemy
set selects script `3400010012` and `radio_e2m5_19` under exact stage filter 1.
`e3m3_q#13`'s two-enemy set selects script `2800010053` and
`radio_e3m3_7` under exact `EntityEvent_OnInteractiveStateChanged`.
`sm2l4m2_q#4d5`'s direct six-child all-`InteractiveCheckInt` group selects
script `23400130004`, `radio_sm2l4m2_3`, and
`cutscene_map02_lv004_lingyuan_1/2/3` under stage filters 1/2/3. The current
stage receiver is union tag `0x00c9`, 18 members; the interactive-state receiver
is tag `0x001e`, 20 members. Stage changes arrive through the one-way
`SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE` server push and expect no reply, while the
interactive-state receiver is a local entity-property event with no packet join
in this path. Neither route proves condition-to-event activation. The first
Lingyuan cutscene's same-script `PreloadCutsceneAction` is auxiliary context,
not playback; unselected occurrences fail closed unless they are that exact
current-build preload shape. The remaining queues are 16 StageChanged and five
InteractiveStateChanged Story files.

The broader direct-carrier census reaches 106 distinct residual
`(levelId, listenerScriptId)` targets and adds zero authoritative owners. Typed
MissionRuntime LevelScript conditions and mission-named LevelData hosts intersect
none; MissionArea roots hit four targets but every one is shared. Region,
domain, dungeon/SubGame, teleport, entity-registry, and residual spawner/HP
carriers likewise stop before an exact mission-to-script consumer. The strongest
current native receiver audit maps all 26 residual families and finds no
serialized receiver `missionId`/`questId` field and no resolved direct receiver
`Process` call into mission or quest methods. The strongest
temptation is `e11m1`'s `SimpleConditionCheckPlayerInLevel(indie_dg011)` row,
where the scene happens to contain only script `36900010001` and four residual
Story files. Native `GetResultWithoutListening` and `_OnCurrentLevelChanged`
consume only current-level identity, so singleton scene inventory is not an
authored activation edge. A future promotion must co-serialize mission/quest
identity with the exact global script or an exact entity/slot inside it; scene
membership, coordinates, sibling scripts, and filename tokens remain rejected.

The asset-object reverse census now closes the decoded unnamed-MonoBehaviour
surface for the 71 remaining Leader-family Story keys. An exact CAB/PPtr pass
expanded 352 initial file hits to 381 candidates and decoded 15 reachable
objects. The only new bridge is
`cutscene_e11m1_dg011_2._timelineName -> _director -> PlayableDirector ->
m_PlayableAsset -> named Timeline`; its complete reachable component carries
no typed mission or quest identity. The former 14 unresolved nonzero PPtrs are
all `m_Script` and are now closed from original Unity data: two resolve in the
loaded dependency process and twelve resolve uniquely after joining expected
external CAB filename plus PathID to the 1,018-row `MonoScript` registry. The
14 MonoBehaviours classify as CutsceneRootComponent,
DirectorNotificationReceiver, ControlPlayableAsset (5), ControlTrack (5),
MarkerTrack, and TimelineAsset; all retain usable serialized TypeTrees, while
none has a usable DummyDll type definition. The fifteenth object is the known
PlayableDirector. This exact classification still produces zero attachments
because the complete component contains no typed mission/quest carrier. The
next exporter task is deterministic multi-process merging of the new compact
scalar/PPtr index, not further inference from names or component proximity.

Exact EOF-bounded spawner consumers now expose constant `SpawnerPtr.id` plus
group/wave keys. The current residual set contains six unique
`OnSpawnerGroupBegin` headers and two `OnSpawnerWaveBegin` headers, all with
null outputs; one group header feeds two Story actions. Separately, the current
AbilityActionData formatter maps `Core_SendBattleSignalToLevel_Data` to tag
`0x0134`, members `6` (the old `0x011f` constant is stale). All 25 residual
listener signal strings have exact producers in current SkillData/BuffData.
These facts prove gameplay producer/consumer wiring, not MissionRuntime
ownership.

The current exact-native unlinked subset contains 16 Story listeners, 12
signal strings, and 20 exact producer actions across 13 original Skill/Buff
files. `SendBattleSignalToLevel.ExecuteInternal` at `0x186d27734` resolves the
signal/value and calls `LevelEventManager.RaiseLevelEvent(0x28)` locally; no
server packet is involved. `OnBattleSignal.Process` at `0x186aa3260` owns only
the signal id and float filter, with no sender/entity/spawner/mission/quest
selector. All 980 MissionRuntime assets have zero relevant identity hits, so
the local producer chain adds no ownership promotion.
The generated receiver view contains 13 BattleSignal nodes and 21 exact
producer-to-receiver routes representing 20 unique producer actions. Every row
retains `serverExchange=false`, no client request, no expected return, and
unresolved mission ownership. This is local runtime causality, not an inferred
mission binding.

The top-level LevelScript task-map decoder is now a generic, fail-closed
current-build parser rather than a `CheckMissionState` special case. Metadata
registration resolves `LevelScriptTaskData.TaskConditionData.condition` to the
root `Beyond.Gameplay.GameCondition`; its formatter has 308 union
registrations, so formatter audits must use `--full-tag-limit 400` (or another
limit above 308) to retain the full tag rows. The root table is distinct from
the overlapping `GameConditionServer` and `GameConditionClient` tag spaces.
The decoder validates the task map interval, declared task/condition counts,
matching dictionary keys, member counts, constant-param envelopes, and exact
trailers before emitting anything. It currently handles the 11 concrete
condition shapes present in the receiver corpus, including string, UInt64,
entity pointer, and entity-list parameters. All 24 receiver scripts with task
maps decode completely as 31 tasks and 54 conditions.
Their 82 distinct task/condition ids have zero MissionRuntimeAsset occurrence.
Thirteen tasks instead match exact level/script/task keys in
`ScriptTaskExtraInfoTable`, which supplies display/tracking metadata, and ten
match `SubGameInstanceDataTable.mainTasks` on the same `bindScriptId`. Every
matched SubGame row has null `dungeonMissionId`. These are typed task and
runtime-scope cross-references, not mission ownership.
An exhaustive typed operand join now resolves 46 of the 54 conditions to 53
authored source objects: 26 unique current-script slot entries and 15 logic-id
entries in `WorldEntityRegistry`, five same-level LevelScript files, three
same-receiver Story keys, three same-level `MissionAreaTable` rows, and one
same-level SpawnerConfig. Exact typed MissionRuntime indexes for the matching
dialog/finish, level/area, level/spawner, level/script, and level/entity
operands yield zero consumers. This is a full negative for the current receiver
corpus, not an ambiguity fallback: the remaining eight rows are property/param
or empty combine conditions with no authored-object operand to resolve.
The task-completion callback lane is closed separately. Current-build metadata
shows that serialized `LevelScriptTaskData` contains only `conditionDict`,
`taskType`, `needManualCheck`, and `canBeTracked`; nested
`TaskConditionData` contains only `isMainObjective`, `objectiveEnum`, and the
condition. Callback delegates exist only on the runtime `TaskCondition`
object. A whole-GameAssembly current-fallback direct-call census resolves the
completion registration chain exclusively as
`CheckLevelScriptTaskFinished._TryBindScriptTaskProgChangeCallback ->
LevelScriptRuntime.SetTaskMainObjectiveIsCompleteChangedAction ->
TaskCondition.AddOnIsCompleteChangeAction`. Its progress callback reaches
`MissionSystem.UpdateObjProgress`; it does not enter an ActionMap or Story
playback method. Only two MissionRuntime conditions use
`CheckLevelScriptTaskFinished` (`c17m2` task `d800b872` and `sm1l3m3` task
`fbb9e474`), and neither exact level/script/task tuple matches any of the 31
receiver tasks. The activation-frontier v5 report now checks this typed tuple
directly and records zero consumers.
The current installed IFix payload does not reopen either negative. Its
82,021-byte decoded `Gameplay.Beyond.patch.bytes`
(`737134081e06371f13c073988547e887037fccf2f57e1052be35dd255d27bc21`)
parses completely as 30 fixed-method targets plus two anonymous storeys with
zero trailing bytes. Exact target and explicit-reference scans find no selected
receiver-ownership, `LevelScriptRuntime`, `ScriptTaskRuntime`, `TaskCondition`,
`CheckLevelScriptTaskFinished`, server-placeholder, or objective-progress
replacement. Two `MissionSystem` targets operate on HUD display orders, while
the dialog/cinematic targets—including
`DialogManager._DoPlayCinematicNode`—remain playback implementation without a
mission/task/LevelScript identity. Re-audit on any patch-hash change; the result
does not authorize a graph edge.

The existing exact positive remains:
`map02_lv003/23300090001` decodes task `cf5a771c`, condition `cb696abe`, and
`e7m4 Equal Completed` from root union tag `0x67` / seven members. A separate
exact black-screen action exists in that script, but no control edge joins the
task condition to it. None of the 24 native receiver task maps contains
`CheckMissionState`; their entity, spawner, dialog, destination, property,
stage, monster, and combine conditions are evaluation dependencies rather than
mission owners. Native mission-state evaluation reads the synchronized local
MissionSystem cache; `SC_SYNC_ALL_MISSION` and `SC_MISSION_STATE_UPDATE` are
independent upstream pushes, not replies to a condition.

The full battle-signal ownership pass reaches 36 producer actions in 27 files
(24 SkillData, three BuffData). Exact current AbilitySystemData skill lists
resolve 31 actions across 22 SkillData files to enemy templates: agtrinit 6,
palesent 6, palecore 1, reaper 16, and klhound/klhog 2. The five remaining
actions are two agtrinit subskills and three buff producers whose typed
intermediate owner is incomplete. None reaches a complete typed producer ->
owner -> selecting-spawner -> MissionRuntime chain. Agtrinit and palesent
have no exact spawner/mission edge; palecore's `bossstart` resolves to a
palecore skill despite a palesent-shaped listener context; reaper lacks a typed
listener-script mission owner in `indie_dg002`; and hound/hog configs in
`map02_lv008` are non-unique. Native execution carries only sender, signal
string, and float through the local level event. This adds zero Story
attachments.

`LevelEvent_OnSpawnerComplete` is also exact for the current observed 53-byte
shape: one constant `SpawnerPtr.id`, a null output, and EOF. Runtime completion
comes from `SC_SCENE_MONSTER_SPAWNER_COMPLETE { sceneNumId, spawnerId }` and is
a server push. The maintained Story join accepts a mission context only when
that id has one current same-level SpawnerConfig and its authored ASCII entity
identifiers contain exactly one delimited current MissionRuntime id. This
recovers `radio_gm02m20_19 -> gm02m20`; it does not select a quest.

The nine residual group/wave Story playbacks remain unowned after a full typed
spawner audit. They reduce to eight exact headers in
`map02_lv007/10200260001`, using spawners `10200260001/4/5`, groups
`101/201/601/701`, and waves `4/5`. SpawnerConfig, wave/group/action/settings,
enemy-library, and `LevelSpawnerInstData` schemas carry scene/spawner/wave and
owning-script identity but no mission or quest field; five MissionRuntime
assets share the level and none references those script/spawner ids. One real
cross-script dependency was recovered: LevelScript `10200060009`, task
`5f624bcc`, condition `87cbeaa6`, uses GameCondition union tag `0x54`
(`CheckLevelScriptStageReachMax`) with `scriptId=10200260001` at raw offset
`0x431`. This proves that one script waits for the generic spawner script to
reach maximum stage, not that either script belongs to a mission. It adds zero
Story attachments.

The same original spawner data does recover chronology without recovering
ownership. The installed generated formatters give exact eleven-field wave and
twelve-field group layouts. A fail-closed decoder uniquely consumes all nine
waves and 20 nested groups in `sc_map02_lv007_10200260004`; action maps remain
opaque and no OCR/manual input participates. Installed
`TimelineWaveBlock.InitWave`, `TimelineGroupBlock.OnInit`,
`TimelineGroupBlock.AllowToStart`, `TimelineWaveBlock.Tick`, `StartWave`, and
`StartGroup` establish group-list predecessor resolution, named PartKilled
targets, and synchronous wave/group-begin callbacks before group action ticks.
Together with the authored wave kill gates, this produces one wave-to-wave and
five wave/group cross-gate Story-order edges. The fifth group edge carries an
exact local relay: group `801` action `105` raises current-script custom event
`TigerStart`, header `140` is the exact same-script listener, and its typed
path reaches cutscene action `151`. Wave 8's named PartKilled dependency on
wave 7 therefore proves `radio_e11m1_45 -> cutscene_e11m1_tiger`. It does not
order the two Story listeners attached to the same group-201 event and does
not cross the missing LevelScript-to-MissionRuntime ownership boundary. The
current Persistent IFix target table contains no `SpawnerRuntime+Timeline*`
replacement.

Additional exact listener schemas now expose their bounded meaning without
inventing mission ownership: `OnTeleportFinish.actionId`,
`OnSquadInFightChanged._inFight`, `OnEntityCastSkill` entity/template/target/
skill filters and outputs, `OnAnyEntityDie` list/filter fields,
`OnSpecificEntityDie._filterEntity`, and the encounter-battle/skip-popup
families. Exact current custom-event producers are also separated by domain:
`RaiseCustomScriptEvent` targets `CURRENT_SCRIPT_ID`,
`RaiseCustomLevelEvent` dispatches locally, and
`SpawnerRuntime.TimelineActionRaiseEvent` calls `LevelEventManager.RaiseLevelEvent`.
For the residual Story set, exact local producers cover 8/16 ScriptEvent files
(nine producer/listener pairs because one file has two) and 1/3 LevelEvent
files. None of the seven producer-backed LevelScript ids occurs in any current
MissionRuntime asset. The other eight ScriptEvent and two LevelEvent files have
no matching authored `RaiseCustom*` producer. The transport fields are only
event key, optional arguments, and for ScriptEvent a LevelScript receiver; they
contain no mission, quest, or server identity.

The residual `radio_e1m8_4` cast-skill record also establishes an important
serialization boundary: its exact receiver is a 160-byte
`LevelEvent_OnEntityCastSkill` subtype prefix followed by 343 bytes of the
enclosing script container. The decoder now validates the subtype prefix and
reports the trailing container separately instead of requiring receiver EOF or
scanning the whole record. Its filter mode is disabled and the decoded fields
are outputs/local event state, so the row supplies a precise receiver selector
without inventing a target, mission owner, or server exchange.

Guide-group playback is now separated into its two native ownership modes.
ActionBase union tag/member-count `0x0304/0x09` is
`ManuallyStartGuideGroup(_groupId)`. It calls
`GuideSystem.ManuallyStartGuideGroup`, which enters
`_TryAddProcessingClientOnlyGuideGroup`. On completion,
`GuideSystem._CompleteCurGuideGroup` handles that client-only branch locally
and skips construction of `CS_COMPLETE_GUIDE_GROUP`; only non-client-only
groups use the request and later server handler. `LevelEvent_OnGuideGroupComplete`
then compares its exact serialized guide id locally before continuing its
action chain.

`CheckGuideGroupComplete` itself is a six-member MemoryPack condition carrying
the common scope/id fields followed by `_completeType` and `_guideGroupId`.
Its condition type is `11` (`GuideFinish`). `GuideCompleteType` is `All=0`,
`Manual=1`, and `AutoClose=2`; the current MissionRuntime corpus has 37
condition occurrences across 21 missions, 36 unique group ids, no missing
constant group id, and every row uses `All`. The check reads completed server
groups and current-scope completed client groups, then listens for the local
completion event. Server-backed groups send
`CS_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClose }` and receive
`SC_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClosed }`; these payloads carry no
mission, quest, or condition id. The Mission Pipeline now retains the authored
group/mode facts and renders both the server-backed exchange and the distinct
manual client-only bypass.

The five residual guide-completion Story files use five exact group ids. Four
groups have an exact manual-start producer: the three `e0m0` tutorial producers
have no validated mission host, while `guide_group_camille_skill_intro` starts
in `map01_lv007/2800340004`, whose mission-named LevelData member-22 host is
`c33m1`. That group also has two exact Story listeners,
`radio_c33m1_37` and `radio_c33m2_30`, in different LevelScripts. The global
completion id therefore does not select the second listener's mission. The
remaining `guide_group_miasma_ghost` has no exact manual-start action in the
current LevelScript corpus. The maintained join fails closed on multiple Story
targets, multiple producers, or a missing unique producer host; this pass adds
zero attachments and never renders a server exchange for a manual guide.

The residual combat/encounter pass covers 17 unique Story files, 18 family
memberships, and 30 exact event-to-playback routes across
`OnEntityCastSkill`, `OnEntityHpChanged`, `OnAnyEntityDie`,
`OnSpecificEntityDie`, `OnEncounterBattlePartBegin`,
`OnSquadInFightChanged`, and `OnSkipBattlePopupConfirm`. Exact
constant targets resolve through the current world/entity/template graph where
present, including slot `40021`, three `eny_0061_palecore` death entities, and
one `eny_0063_agmelee2_001` entity. Dynamic getter targets and output-only
headers remain explicitly dynamic. The native manager registers these headers
from a LevelScript pointer/context and dispatches local `GameLevelEvent` plus
`EventParams`; all 21 audited producer/manager bodies lack a mission ownership
bridge. None of the 12 exact owner ids, targets, or configs occurs in the 980
MissionRuntime assets, and all 12 validated LevelData host joins return no
row. Ten memberships remain ambiguous and eight are structurally bounded;
zero are promotable. Reused boss-rush dungeon bindings have empty
`missionWhitelist` fields. These events prove local combat conditions and
presentation timing but add no mission/quest attachment or server payload.

Patrol playback is also exact at the local gameplay layer. All six former residual
`NpcPatrolCheckpointReach` Story files have a same-LevelScript
`NpcPatrolStart(alias, patrolId)` action, an exact current `NpcPatrolData`
record, and a listener point index within the recovered patrol point count.
Their maintained listener decoder now exposes the dynamic NPC property path,
patrol id, checkpoint index, NPC-position output, and local/no-server boundary.
Original LevelData type-13 BriefData properties resolve `Robot2`, `Robot3`, and
`robot` to world entities `23200013030`, `23200013387`, and `23200010664`;
all are type-256 elf-machine entities rather than NPC proxies. A stricter
tracking re-audit found 14 qualifying same-scene, non-script
`EntityTrackingInfo` rows for their local entity ids. Every row belongs to
`sm2l5m1`, while multiple quests track each entity. The maintained join now
promotes the six files to one non-owning `sm2l5m1` mission shell only after the
receiver, property/entity, same-script producer, framed patrol row, checkpoint,
registry, and tracking mission union all validate. Candidate quest sets and
visibility filters remain evidence; they do not become activation, playback,
completion, or ownership. `NpcPatrolStart`, checkpoint dispatch, and Story
playback are local, with no client request, server push, or expected reply.
The remaining scripted-character case closes the longer chain:
`radio_c27m4_9` listens for `patrol2end` in
`dung02_rdg001/26900000008`; `ScriptedCharPatrolStart` targets alias
`tangtang` and patrol `26900000020`; that patrol's second point contains
`CharPatrolPointAction` member-count 18 with native type enum `6=SendEvent`
and the exact `patrol2end` key. No target LevelScript id, patrol id, or detail
id occurs in qualified MissionRuntime tracking. A same-level NpcProxy whose name contains
`tangtang` is authored for `c27m4d5`, but the serialized patrol alias is not a
typed proxy id and no native alias-to-proxy resolver has been recovered. That
row remains candidate-only and unowned.

After the six NPC-checkpoint promotions, the remaining lifecycle/navigation
queue covers 11 Story files and 11 exact listener occurrences across guide
completion, scripted patrol, teleport finish, dialog exit, and script complete.
It yields zero further promotable rows, two ambiguities, and nine
proven-negative joins. The two ambiguities are the Camille
guide id's two-listener fan-out and the untyped `tangtang` alias-to-NpcProxy
candidate above. Native playback semantics are local: NPC checkpoint dispatch
uses `GameLevelEvent.ON_NPC_CHECKPOINT_REACH=0x2a`; ScriptComplete inherits
SELF scope and `UpdateRuntimeState` raises local enum `8`; DialogExit remains
distinct from `LevelEvent_OnServerDialogExit`; and teleport's listener
`actionId` is not the synchronized `tpUuid`. A source-graph ownership scan over
the 15 target scripts finds no direct typed mission or quest edge.

The remaining interaction/property receiver audit closes 11/11 exact
`EntityEventHeader -> native control path -> Story` chains. Eight constant
targets resolve to current world entities; `radio_e3m3_7` resolves script
`2800010053`, slot `40002` to `int_narrative_iron`; and the dynamic
`radio_e2m5_2` `liftButton` parameter resolves through the same-script
LevelData BriefData property map to world entity `3400010152` and
`int_lifter_button`. `radio_gm01m6_7` instead targets an authored Leader box
volume at slot `80001`, not a registry entity. Across the current corpus these
owners have zero exact MissionRuntime objective/condition/tracking references,
zero of 471 typed `EntityTrackingInfo` rows match, and NPC/LUT/spawner ownership adds no
edge. Nearby mission coordinates are not identity and remain rejected. The
receiver bodies are local consumers with no MissionRuntime or protobuf send
call; this does not claim that the underlying save property can never be
synchronized elsewhere. All 11 remain unowned.

The broader entity/property audit covers 20 unique Story keys across seven
event families and recovers an exact serialized event-to-playback route for all
20. The four `ScriptEvent_OnPropertyChanged` listeners are SELF-scoped with
authoritative same-script BriefData config, while all four
`ScriptEvent_OnBBVariableChanged` keys have exact same-script `SetInt`
producers and local dataflow. `radio_sm2l6m1_29` has exact
`OnRuneColumnMatch` component semantics and two typed rune-column source
entities (`25000040034/35`), which remain receiver-ambiguous. Searches across
980 MissionRuntime files, 490 mission sidecars, all typed tracking rows, and
validated Mission/MissionArea LevelData hosts produce no identity join. The
mapped handlers are local subscriptions/dispatch and call no protobuf request,
network send, or MissionRuntime ownership method. All 20 remain bounded and
zero are promoted.

The teleport boundary is now complete enough to rule out a false Story join.
`CS_SCENE_TELEPORT` sends `sceneNumId`, position, rotation, teleport reason,
pass-through data, `tpPosId`, and one reason-detail case. The server applies
`SC_SCENE_TELEPORT` with object ids, scene/transform, server time, reason,
`tpUuid`, and pass-through data; after local completion
`TeleportProcessor._OnTeleportFinish` at `0x184970510` sends
`CS_SCENE_TELEPORT_FINISH { tpUuid }`. Separately,
`LevelEvent.OnTeleportFinish.Process` at `0x186abe000` compares its authored
string `actionId` filter with the local event's action id. That string is not
`tpUuid`, is absent from all three network payloads, and carries no
mission/quest identity. The residual teleport Story listeners therefore remain
exact native playback routes without a pipeline owner.
No audited custom producer carries a mission/quest id.

The top-level `LevelScriptTriggerVolumeData` dictionary is now exact for the
current Leader subtype. Union tag `1` has member count `8`; the base fields are
`enterCheckOnGround`, `exitShapeStartIndex`, `isImportant`, the typed shape
list, `slotId`, `triggerCountLimit`, `triggerOnPole`, and `waitSrvRes`.
Key/slot equality, the `80000..89999` slot range, shape member layout, field
ranges, and an end cursor exactly at EOF are mandatory. A guarded wrapper form
is also decoded only when its fixed prologue and inner EOF-bounded map match.
MissionArea coordinates are joined by authored level identity through
`LevelBasicInfoTable.idNum`, not by assuming a globally unique area id. The
pipeline currently emits 79 exact full MissionArea/Leader-trigger geometry
context rows plus 71 exact `PosTrackingInfo`/trigger-center rows. Full area
matching requires position, shape type, size/rotation or radius, selected
trigger slot, and one mission; position-only matching requires the exact center
to select one mission and does not claim shape equality. Both prove local
client context, not that entering the volume completes the quest or describes
a server exchange.

Current client/server boundary recovery is also explicit but remains separate
from Story ownership. Client global-variable writes send
`CS_UPDATE_CLIENT_GAME_VAR { key:int32, value:int64 }`; server updates or
confirmations arrive as
`SC_UPDATE_GAME_VAR { key:int32, value:int64, type:int32 }`, with `type` kept
as an uninterpreted discriminator. Spawner wave start sends
`CS_SCENE_MONSTER_SPAWNER_BEGIN_WAVE { sceneNumId:int32, spawnerId:uint64,
waveId:int32, clientTimestamp:double }` and receives the same identity tuple in
`SC_SCENE_MONSTER_SPAWNER_BEGIN_WAVE`; completion is a server push with scene
and spawner ids, followed by the client's wave-confirm message carrying the
wave id. These exchanges are asynchronous. Local spawner group-begin and
global-variable callbacks are derived runtime events, not extra network
messages. Leader trigger-volume touch sends
`CS_SCENE_TOUCH_TRIGGER_VOLUME_REQ { sceneNumId, scriptId, scriptLocalId,
isLeaveAction }`; wait-server paths receive the same identity fields in
`SC_SCENE_TOUCH_TRIGGER_VOLUME_RSP`. Independent server state pushes use
`SC_SCENE_MODIFY_TRIGGER_VOLUME_SYNC` with repeated `{ scriptLocalId,
isHidden, triggerCount }`. These packets identify a LevelScript slot but carry
no mission/quest id. Protocol rows alone therefore do not attach Story; the one
SpawnerComplete join above additionally requires exact authored config
ownership.

`DialogBriefInfoForMemoryPack` is also exact for the current table. Its nine
serialized members are `afterMaskBlendData`, `beforeMaskBlendData`, `dialogId`,
`dialogType`, `enableSeamlessStartInSameFrame`, `interactText`, `npcProxyIds`,
`useBlackScreen`, and `usedDialogTimelineIds`. Sequential decoding of the
2,633-entry first `DialogIdTable` map yields 413 dialogs with 425 authored
Timeline-list elements (424 distinct dialog/Timeline pairs), including the
valid `f_dlgtl_*` prefix. Timeline ownership must come from member 9, not from
rewriting or scanning a dialog name.

### Family status

The following table summarizes durable status without reproducing every old
per-session count.

| Family | Current recovery status |
| --- | --- |
| `DialogIdTable`, `ModelTable`, `ModelRadiusTable`, `InteractiveTable`, `WorldEntityRegistry` | Exact or exact for their maintained top-level/index layouts; InteractiveTable's two native maps and DialogBriefInfo's nine-member Timeline ownership field are decoded sequentially. |
| `NavMesh/*/LunaArea` and `NavMeshStateContainer` | Exact for the observed current variants. |
| Selected mission-area, teleport, non-generated table, and compact lookup roots | Exact family-specific readers where maintained. |
| `LevelConfig` | Verified ids, default-state data, path counts, map ids, and numeric transform/bounds tails; middle path/grid body remains bounded. |
| `LevelData` | The 43-member top-level count and member-22 LevelScriptBriefData dictionary are exact. Typed MissionArea sub-data parents can scope a validated file shell when all roots agree; member 23 is empty in the current corpus. Most other heterogeneous members remain partial. |
| `LevelScriptData` | Large action/condition surface has typed readers, the complete current ActionHeader union table, exact Leader trigger-volume maps, local ScriptActive/StageChanged lifecycle layouts, and exact constant GroupBegin/WaveBegin consumers; unknown action families and some chain boundaries remain. Story ordering conclusions belong in the Story note. |
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

The separate `DynamicStreaming/PC/Scene/*/fb_main_*.bytes` family is now typed
from the installed FlatBuffer accessors rather than the generic chunk probe.
Across 457 current main chunks, `FBDynamicSceneSingleGrid` exposes typed
`MissionCondition`, `IdComp`, `MissionControlComp`, `ScriptControlComp`, and
`RootComp` vectors. Native `DynamicSceneIdSystem.AfterRegisterComp` registers
`IdComp.UniqueId` only in the DynamicScene logic-id-to-entity-id map, while
`DynamicSceneMissionControlSystem` reacts to mission/quest state changes. The
scan found 387 mission-controlled roots and 125 numeric identities also present
as LevelScript ids; 72 of those touch 218 Story occurrences in the effective
Persistent LevelScript root. The maintained current
audit is
`reports/story/recovery/dynamic_scene_mission_control_audit.{json,md}` and
streams the effective installed Persistent overlay rather than depending on a
saved scratch dump. The occurrence reader now uses that same Persistent root;
the former mixed-root scan used StreamingAssets offsets for two patched
`map02_lv008/23100350005` actions and omitted two additional tagged action-list
occurrences. The additional `dlg_f1m32_15` and `_15_1` rows still lack a mapped
native action class, so they are occurrence evidence rather than typed playback.

The separate action-bridge audit at
`reports/story/recovery/dynamic_scene_levelscript_action_bridge_audit.{json,md}`
recovers a genuine identity crossing in the opposite direction. Current
`ShowSceneDecorationNew` and `ShowSceneDecorationWithHandle` serialize
`Param<DynamicSceneEntityPtr> _targetDynamicEntity` followed by
`Param<bool> _visible`. Requiring action-list membership, constant parameters,
the exact 10-member union layout, and complete payload consumption leaves one
Story-bearing self-target: `map02_lv001/10100282001`. Its exact slot-80001
leader-enter chain runs `dlg_c27m3_6` and then
`ShowSceneDecorationNew(10100282001, false)`. This proves that the LevelScript
addresses the same DynamicScene root and that both actions share local control
flow. It does not prove that `MissionControlComp` activates the LevelScript
header, so ownership/order remain unresolved and `missionGraphAction=none`.
The full current constructor order names the remaining component refs rather
than leaving numeric placeholders: type 18 is `FBDynamicSceneTriggerComp`,
type 30 is `FBDynamicSceneResourceComp`, and type 54 is
`FBDynamicSceneBlightMiasmaComp`. Every one of the 387 mission-controlled
roots, including all 125 LevelScript-id and 72 Story-bearing matches, carries
only IdComp, MissionControlComp, ResourceComp, and BlightMiasmaComp; none
carries TriggerComp. ResourceComp serializes resource, mount, navigation, and
LOD groups plus `NavState`; BlightMiasmaComp has only `Empty`. TriggerComp
itself contains shape/radius/center/size/transform and a position-list group,
with no trigger-slot, LevelScript, mission/quest, or Story field. The focused
LevelScript slot `80001` therefore cannot be joined through a DynamicScene
TriggerComp foreign key.

The opposite slot carrier is now exact as well. The same event selector resolves
slot `80001` to the owning `10100282001` LevelScript's embedded
`LevelScriptTriggerVolumeDataForLeader` row: one sphere at
`(-757.75, 234.828, -1185.85)`, radius `59`, trigger-count limit `1`. Current
metadata declares eight fields on the base trigger-volume type
(`isImportant`, `waitSrvRes`, `enterCheckOnGround`, `triggerOnPole`, `slotId`,
`triggerCountLimit`, `exitShapeStartIndex`, and `shapeList`) and zero additional
fields on the Leader subtype. The current eight-member payload is fully
decoded. It contains no DynamicScene, mission, quest, LevelData entity, or
other foreign identity. This is an exact local LevelScript trigger definition,
not a cross-system activation edge; the nearby mission-area matches remain
coordinate diagnostics and are not promoted.

The adjacent `FBDynamicSceneScriptControlComp` is now
closed rather than inferred from its name: current metadata exposes only
`DefaultLoad:int32`, its runtime system indexes DynamicScene component/entity
and logic ids for local decoration/animation/audio/view-state operations, and
zero of the 387 mission-controlled roots co-carries that component. The same
zero therefore holds for all 125 LevelScript-id matches and all 72
Story-bearing matches. This equality is a
useful authored cross-reference but not an ownership bridge: exhaustive native
caller scans found no DynamicScene mission-control/LevelScript-activation join,
and the remaining
`23200013031` candidate is a mission-controlled world-resource root with no
script component. Its validated LevelData host is the generic `sub_01`, not the
mission-named `sub_sm2l5m1`. The three `radio_sm2l5m1_21/_22/_23` rows therefore
remain unbound under the original-data-only policy.

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

The current decoded index and frontier live under
`webui/data/decoded/index.json` and
`reports/assets/diagnostics/monobehaviour_frontier_latest.*`; read counts from
those generated outputs rather than copying them here. The frontier remains
concentrated in a small number of template families rather than broad across
the corpus.

The tail audit now distinguishes byte-boundary failures from
`semantic-partial` layouts. All observed projectile roots in both source roots
consume their structured tails exactly and belong in the semantic-monitor
queue, even though their enclosing files remain partial for unproven enum/hash
names, omitted metadata fields, and runtime meaning. The
`AbilityEntityTemplateData` inherited prefix, opening, and 92-byte
`surroundingConfig` are now byte-proven across the full current family; the
remaining body from `followMountPointConfig` is the next parser target.
Character target selector/settings payloads and the rare enemy EffectActionCfg
tail are structurally complete and move to semantic monitoring.

### Proven gameplay payload advances

- Focused character `AbilitySystemData` rows consume the validated parent
  structure through skill bundles, command mappings, combo conditions, UI
  data, buff lists, entity blackboards, skill-camera configuration,
  post-camera fields, preload ability entities, and potential buff ids.
- `AbilityEntityRootComponentData` is exact for the observed current layout.
  All 162 enclosing `AbilityEntityTemplateData` roots now decode their mirrored
  id/name, faction word, counted GameplayTags, recycle/fade fields, and 833/833
  component RID links. The guarded ability-specific opening through
  `useFrameTick` now consumes 60 bytes in 158 roots and 80, 84, or 104 bytes in
  four keyed Blackboard variants. All 162 linked exact root-component mirrors
  match for its first five fields; the remaining six scalar names stay visibly
  qualified as IL2CPP metadata-order evidence. This removes 9,852 bytes (9.01%)
  from the former raw tails. The following `surroundingConfig` now consumes an
  exact guarded 92 bytes in all 162 roots, with 14 linked movement mirrors and
  10 non-consuming next-field rotation mirrors; residuals are now 336-1,084
  bytes and stop before `followMountPointConfig`. Field order/ownership is
  proven, while enum/hash runtime meanings remain inferred.
- Physics and observed NavMesh-obstacle component shapes have guarded readers.
- `EffectActionCfg` now has exact guarded readers for the observed dead-effect,
  projectile alert-effect, projectile effect-list, and rare 80-word
  omit-useScaleBB tail variants. The rare shape occurs only in the mirrored
  `data_eny_0092_slbomb` roots and keeps its field/enum meanings inferred; the
  enclosing EffectActionCfg remains semantic-partial. The observed layouts are
  not interchangeable.
- Projectile component recovery covers the stable prefix, move-mode maps,
  Bezier records, all six effect lists and show flags, alert effect, seven sound
  hashes, and final distance/factor fields. A full current-family replay across
  both roots consumed every observed tail exactly with no raw fallback or
  unparsed node. Remaining projectile `$partial` markers are semantic confidence
  boundaries, not unfinished byte readers.
- `SelectorData` and FindTarget actions are byte-proven in MemoryPack BuffData.
  The separate Unity managed-reference `SelectorData`, `TargetSettings`, and
  nested `DirectionSettings` layouts are now also exact-consumed across all 74
  current CharacterTemplateData occurrences: SelectorData is 72 16-byte empty
  variants plus two 24-byte one-validator variants, TargetSettings is 24
  100-byte plus 50 108-byte variants, and DirectionSettings is uniformly 40
  bytes. Enum/hash names and unobserved non-empty post-processor/context or
  advanced source/target variants remain semantic/fallback boundaries.
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

WebUI-relevant and exhaustive builds:

```bat
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
python tools\endfield_source_graph.py build
```

Useful cost controls:

- `--skip-gameplay`
- `--skip-asset-maps`
- `--relevant-asset-maps`
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

The current exhaustive cross-check reached 5,797,647 nodes, 11,136,077 edges,
5,845,781 aliases, and a 10.78 GB database. Generic AssetMap identities account
for most of the excess: millions of unrelated Unity rows expand into graph
nodes, aliases, and reverse edges.
The WebUI-relevant scope selects 1,140 exact `(source, PathID)` identities from
the same original maps, including complete selected rows so name/export-base
fallback behavior remains available. The canonical relevant rebuild completed
in 1,013.5 seconds with 1,860,722 nodes, 4,401,960 edges, 2,285,532 aliases,
a 4.09 GiB database, and all 1,140 required identities matched.
Presentation (3,893 nodes / 8,373
edges) and Combat (1,086 nodes / 1,071 edges) payloads were canonically identical
between relevant and exhaustive graphs. Exhaustive mode remains the evidence
source for broad generic Unity-object/PathID investigations; changing graph
scope never substitutes OCR or external evidence for original game data.

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

Mission Pipeline atmospheric envTalk context is now a first-class graph
relation sourced from `webui/mission_pipeline/env_talk_context`. The canonical
generated inputs contribute 490 mission-scoped rows across 380 unique context
nodes, 359 Story files, 64 missions, and 52 literal condition quest ids (51
resolve in MissionRuntime; `f1m9d3_q#15` remains an explicit unresolved
reference). The path is represented as mission/quest state -> context ->
switcher group -> cluster -> envTalk -> Story. It emits zero direct
mission-to-Story edges and every relation records
`ownershipStatus=non_owning_context`, `playbackOwnership=false`, and
`orderEvidence=false`. This makes the recovered world-state dependency
queryable without turning availability into ownership, playback, chronology,
completion, or server-exchange evidence.

Mission Pipeline's unresolved native playback frontier is also first-class
graph evidence under `webui/mission_pipeline/native_runtime_receivers`. A row
is accepted only when its exact current-build MemoryPack classification,
unresolved-owner status, unique `(levelId, listenerScriptId,
listenerHeaderLocalId)` identity, native action, Story key, and LevelScript
source path all agree. Current inputs contribute 158 receiver nodes and 182
receiver-to-Story placements covering 153 Story files, 25 event families, and
23 levels. These edges set `playbackEvidence=true` but
`missionStoryBinding=false`, `missionOwnershipEvidence=false`,
`playbackOwnership=false`, and `orderEvidence=false`; the ingestion emits zero
mission or quest edges.

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

The maintained Progression WebUI payload now materializes this evidence as
15,691 typed nodes and 37,970 direct, endpoint-valid relations across 9,836
browsable roots. It includes character and weapon upgrade structures,
equipment stages, item costs/use/obtain paths, reward bundles and probable
entries, drop pools, and wiki enemy drops. Each relation retains its source
table, row, and field path; the graph intentionally makes no live availability,
account-state, probability, or optimal-plan claim.

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
and level-script slots. The exact EntityTracking join above additionally
recovers client navigation/configuration context, but still does not reconstruct
the live world, server quest policy, or a general scene simulation.

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
dated inventory snapshot. Projectile inspection, combat relationships, and
factory/economy browsing are landed with evidence confidence and the
static/runtime boundary preserved, and the static World explorer now exposes
authored placements and references. Combat also consumes the exact
AbilityEntity inherited prefixes and all 833 component RID links, but excludes
the remaining bytes from `followMountPointConfig` onward. Deeper combat labels
remain gated on the recovery work below:

1. Continue `AbilityEntityTemplateData` from the now-guarded
   `followMountPointConfig` boundary. The rare enemy EffectActionCfg omit-useScale
   tail is now exact-consumed in both mirrored roots; retain its field/enum
   meanings as inferred.
   Keep structurally complete projectile and selector/target-settings layouts in
   semantic monitoring unless a future payload variant fails an exact guard.
   The projectile WebUI already ships from the byte-complete fields; keep its
   inferred labels qualified until runtime meaning is proven.
2. Decode the remaining 48 ambiguous BuffData action chains per root, starting
   with repeated action families such as FinishBuffAdvanced,
   CheckBuffStackNumAdvanced, HitStopAction, and SpawnEnemyAction.
3. Trace one bounded combat formula from authored table/decoded payload through
   the actual runtime consumer and evaluator order. Keep display transforms and
   raw scalars separate.
4. Recover IL2CPP accessor names for the dominant world-streaming FlatBuffer
   root before promoting more field labels or scalar/struct vector decoders.
5. Expand direct reverse links only when they answer a maintained query. The
   combat relationship explorer is the current maintained consumer: prefer a
   typed graph edge plus smoke test over a standalone memory report.
6. Compare StreamingAssets and Persistent binary families when patch behavior
   matters, using hashes and schema-aware diffs rather than assuming mirrors.
7. Extend the landed factory/economy browser only when new tables add a durable
   maintained query. Retain raw ids/values and do not promote inferred
   throughput equations or live shop/activity state.
8. Improve per-source/per-object warning attribution if an actual clean-export
   certificate becomes necessary; do not infer it from aggregate success.
9. Continue from the exact `gameId -> SubGameInstanceData` packet/table join and
   the proven WorldChallenge quit consumer. One narrow typed co-carrier is now
   recovered: LevelData `RadioTriggerZoneData` directly pairs four radio ids
   with mission-state boundaries and the native playback consumer, producing
   six context placements. The new `LevelData.airWalls` decoder adds the
   stronger predicate-rich form: 58 accepted authored rows, 20 Story radios,
   30 checked missions, and 61 record-level non-owning attachments, with two
   inconsistent mixed-type groups rejected. Two exact member-20 narrative
   entities also pair
   `radio_c16m4_50/51` with the `c16m4d5` FX-change mission key through the
   typed template and native NarrativeComponent. These are local state-gated
   playback dependencies, not the missing
   generic mission/quest-to-LevelScript activation registry. The bounded native
   direct-call and protocol audit found no such generic co-carrier:
   MissionRuntime actions contain no
   LevelScript operands, LevelScript activation contains no mission identity,
   script packets carry scene/script ids without mission ids, and mission-event
   packets carry mission/event ids without a script address. Lua adds two exact
   system cutscene consumers but no mission owner. The tempting
   `TeleportParam` co-carrier is now closed too: current producers never
   co-populate mission/script identity and current consumers never read its
   `missionId`. Search other shipped config, indirect-dispatch, or
   asset-consumer registries for a carrier that resolves both identities.
   The protobuf message registry is now closed as another distinct surface:
   recursive runtime-type traversal across all 983 current enum-backed CS/SC
   classes finds no mission/quest + LevelScript/Story co-carrier. Its only
   active weak scene candidates feed `CharacterPositionCorrection` from the
   synchronized role snapshot and are not authored hosts. Do not repeat either
   the message-schema or role-snapshot join until the metadata, binary, or IFix
   hash changes; prioritize non-protobuf server-state/config and asset-consumer
   registries. For those registries, reuse the AirWall admission rule: require
   one completely framed typed object that co-carries the state predicate and
   Story consumer, then prove both native consumption lanes before adding even
   a non-owning context.
   `MissionOptionData` no longer belongs in that queue: its two fields drive
   mutually exclusive action branches and no current authored instance exists.
   Reopen only on a binary/export/IFix change.
   The nested mission-property carrier no longer belongs there either.
   `MissionRuntimeAsset.properties` has no script pointer, MissionSystem
   synchronization writes `MissionData.propertyDict`, and `m_scriptPtr` is
   attached by LevelScript event subscriptions rather than mission handlers.
   Reopen only on a binary/metadata/export/IFix change.
   The current ten missionless SubGame playback rows are now closed across
   their complete exported exact-reference and receiver-task surfaces: nine
   unique Story files across fourteen placements, one non-owning activity
   mission association, one quest unlock, one mission-state unlock, five
   prior-challenge gates, and zero MissionRuntime task consumers. The broader
   exact-scene join adds eighteen receiver scripts across six Dungeon/SubGame
   scenes, but thirty-three of forty placements are sibling scripts and the
   `cutscene_e9m3_2` / `e9m4_q#1` mismatch rejects availability as ownership.
   Nine sibling receivers also see a typed `dungeonMissionId`; the
   `c6m3`/`c6m1` and `c13m2d5`/`c13m2` counterexamples reject mission-shell
   inheritance.
   The sibling `missionWhitelist`/`logicIdWhitelist` fields are empty in all
   469 rows. The sole nonempty `proxyWhitelist` belongs to `f1m18d1_1`; its two
   dialogs are already covered by stronger quest-condition/native-playback
   evidence and its NpcProxyEx rows carry no mission id. Do not repeat this
   whitelist census on the current export.
   `conditionalDeathPerformanceEntries` is empty on all 250 DungeonSubGame
   rows. The 16 enabled team-death blackscreens use only the generic
   `dungeon_blackscreen_text` key or blank values, so this tail adds no
   `black_*` Story carrier.
   Prioritize a different registry surface
   rather than repeating these SubGame/task/display joins.
   Do not revisit the current loading-pipeline carrier unless the installed
   binary or IFix payload changes. Never promote Story naming, OCR, gameplay
   observation, or same-LevelData siblings into that missing identity.
   The new `MissionRuntime WorldEntity condition -> WorldEntityRegistry ->
   LevelScriptBriefData.refWorldEntityIdList` route is the model for further
   recovery: require a complete typed group, globally unique mission/quest
   ownership, and unanimous same-level script hosts, then label the result as
   context unless native execution proves activation.

When one of these changes lands, update this file's current conclusion and
queue. Put detailed counts in generated reports and remove obsolete session
notes instead of creating another distributed recovery memo.
