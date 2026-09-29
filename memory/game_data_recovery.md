# Game-data recovery

This topic owns durable conclusions about installed data formats, gameplay and
audio semantics, native consumers, and the source graph. It does not own WebUI
presentation, page build commands, or AnimeStudio implementation mechanics.
This file is the entry point; per-family evidence lives in
[`game_data/`](game_data/README.md), and the mechanics of each reader, gate and
validator live in its module docstring and reviewed contract under `scripts/`.

## Why this topic remains

Many evidence contracts are shared by several pages or exist before any page
projection: overlay behavior, binary framing, native build gates,
runtime/static distinctions, and cross-domain graph provenance.

## Refresh and evidence rules

```bat
python -m scripts.game_data.extraction.verify_export_freshness
.\export.bat --from-game
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Run `--from-game` only when the user asks for an installed refresh.

- StreamingAssets is the fallback; Persistent is the active overlay. A changed
  logical path replaces its fallback file as a whole unless a format-specific
  contract proves record-level merging.
- Native claims require the selected `GameAssembly.dll` plus
  `global-metadata.dat` gate. Missing or mismatched inputs skip that evidence
  and leave the last validated report untouched.
- Metadata default blobs require their primitive backing type: decoding a
  byte-backed enum as a signed compressed `Int32` invents negative IDs. Resolve
  the backing type from the selected MetadataRegistration first; the native
  enum helper supports reviewed byte and `Int32` cases and fails closed.
- A source-only classifier does not inherit the native gate because native
  evidence once motivated it. Direct gate callers are runtime-capture identity,
  metadata enum reads, and consumers of pinned methods, code windows, field
  offsets, registrations or native contracts. Current-export Story classifiers
  validate their own tables, object-index stage signatures and fingerprints.
- **`inputSetSha256` identifies one audit run, not the game build.** It hashes
  the exporter binary and absolute asset roots, so it is only a join key
  between one run's VFS summary, ledger and corpus reports. No contract is
  gated on it and tests must read it from their fixture, never hardcode it.
  Whether a contract applies is decided by its `nativeInputs`.
- Hash checks survive only where git cannot guard: the installed build against
  `nativeInputs`, native code bytes against a recorded window or body hash,
  installed game files such as iFix patches, and a generated report against
  its inputs.
- A field name, code address, registration order, hash collision, filename,
  proximity, or available asset is not ownership or runtime execution.
- Preserve source root, logical path, file hash, record offset, parser/schema
  version and validation status through every join.
- Exact parsers require bounded positive fixtures, malformed/truncated/trailing
  negatives, exact consumption, and a current-corpus sweep.
- Build-specific counts, hashes, tokens, addresses and inventories belong in
  reports or versioned contracts.

## Re-resolving a native identity after a client update

A contract pinned to a superseded build is not evidence that its subject is
gone. Only the managed name survives an update, so a stale contract is
migrated by resolving names against the selected build, never by carrying an
address forward. `scripts/game_data/il2cpp/method_resolver.py` owns that
direction and documents the three name classes that drift without a source
change (compiler-generated closures, Burst direct-call wrappers, recorded
display forms). A resolved body extent is the gap to the next method pointer,
an upper bound rather than a proven length; re-resolution restores identity
only, so the old contract's conclusions about the bytes stay unvalidated until
re-derived. Prefer build-independent claims contracts
(`il2cpp/body_claims.py`) for new consumer claims.

## Installed-data model

The installed client exposes overlapping logical data through VFS catalogs and
payload roots. A verified outer VFS boundary proves byte identity and
availability, not the inner payload schema. The full outer VFS audit, Bundle
inner audit, Table dump and JsonData source/export join give a strong
structural baseline for the selected build. Named-schema coverage is narrower,
and no file count measures effective runtime consumers or behavioral/visual
parity. Current denominators live in the generated `reports/animestudio/`
receipts; per-family reader boundaries are in
[`game_data/extraction_payload_boundaries.md`](game_data/extraction_payload_boundaries.md).

Current position of the families with active recovery:

- **JsonData.** The authenticated registry (`scripts.game_data.jsondata_corpus`)
  joins every current logical file to the export by path, length and MD5, and
  assigns each a terminal status. Most families close exact named schemas to
  EOF. LevelScriptData, LevelScriptTemplateData and SkillData keep a
  bounded-partial residue; BuffData has an exact named subset while the rest
  stays format-framed. The last complete combined gate predates the most
  recent LevelScript integrations, so their whole-owner effect is provisional
  until the next full gate. See
  [`game_data/serialization_memorypack.md`](game_data/serialization_memorypack.md).
- **LevelScript.** The sequential owner reader continues through action maps,
  task maps, NPC, enemy and module dictionaries at exact cursors. Each union
  route moves through three steps: an isolated contract and validator,
  registration in the shared ActionMap/layout with production replay, and
  whole-owner closure only through the full JsonData gate. This is
  stored-schema recovery; no stored action proves runtime execution.
- **SkillData.** Native-gated readers close the reviewed ActionGroup interiors
  and rejoin the selected top-level terminal. The live target-set cursor
  capture is complete and loss-free: every reviewed ambiguous source and the
  positive control verify, so no further capture is needed for that set.
  Purrche's below-Potential-3 branch was unavailable on the user's save; its
  stored source and native logic are recovered, its execution is unobserved.
  Separate Wulfa and Seraph cursors, plus one grouped four-source Zhuangfy
  capture, now have source-scoped whole stored-schema joins. Five Zhuangfy
  action routes are admitted to the shared reader under current native gates.
  The newly checked Lizhiyan combo source passes its ActionGroup and selects
  one field-42 terminal boundary, but remains a partial, nonpublishable
  one-source diagnostic. A separately selected Pograni ultimate source now
  replays its formerly unknown `0x0152` action and reaches physical EOF under
  the earlier anonymous terminal shape. A one-file current VFS gate confirms
  the copied bytes, but no live cursor names its terminal fields; it remains
  nonpublishable. Those selected results do not replace the current
  family gate. The residual partial files stop at mostly distinct action tags.
- **BuffData.** A 30-field root reader closes selected cohorts from byte zero
  through source ID and physical EOF when every reached child has a native
  receipt; the admitted cohort set is the branch logic in
  `scripts/game_data/memorypack/buff_root_no_positive.py` and its child
  receipts. Selected positive-heal claymore, BreakPassing event, and equipment
  suit attribute/damage sources now reach exact EOF as local diagnostics;
  the family gate has not been refreshed. Other files keep recursive blockers
  in positive `damageModifier`,
  `attributeModifier`, event-action and finder bodies.
- **ExtendData catalogs.** Both StringPathHash catalogs have current
  cross-format hash joins to VFS filename hashes and BundleManifest asset
  paths; the catalog writer and runtime lookup remain open
  ([`game_data/extend_data.md`](game_data/extend_data.md)).
- **CompressData / AI.** A selected native chain runs from a spawn record's
  template ID through `EnemyTable` to a formatted `AIConfig` load, and authored
  BehaviourTree identities join archive ordinals. No checked producer equates a
  SpawnerConfig library entry's stored `enemyId` with the protocol template ID,
  and live spawn selection stays open
  ([`game_data/extend_data.md`](game_data/extend_data.md)).
- **Video carriers.** Stored `PlayFmvAction.moviePath` values join installed
  Video files through a selected native `f_`/`m_` naming branch; that joins
  authored naming, not an activated scene
  ([`game_data/story_carriers.md`](game_data/story_carriers.md)).
- **Bundles.** Corrected AssetMap container paths resolve the former fallback
  residuals, and the CAB dependency sweep places every mapped external
  reference inside the BundleManifest dependency list; manifest-only edges and
  a live selected load stay open
  ([`game_data/unity_assets.md`](game_data/unity_assets.md)).

Stable cross-format rules:

- Unity object identity is source/CAB plus PathID. A global PathID or basename
  is never sufficient.
- Table ids and localized strings are authored values; they do not by
  themselves prove a runtime consumer.
- Serialized TypeTrees are preferred when exact. `$partial`, `$unparsed`, and
  `$inferred` stay visible and are never upgraded by a later name match.
- Runtime-mutable properties keep their authored initializer but are not final
  action targets unless later writes are excluded.
- Exact spatial transforms prove authored placement, not spawning, activation,
  visibility, or interaction.

## Where the detail lives

[`game_data/README.md`](game_data/README.md) holds the four evidence levels,
the block-to-lane table and the file index. A claim may cite evidence only from
its own level or below; most recorded mistakes read a level-4 meaning off a
level-2 framing. Read
[`game_data/settled_and_open.md`](game_data/settled_and_open.md) before
reopening chunk slot typing or HIRC type coverage.

Per-build member orders live in `scripts/game_data/contracts/`; each reader,
gate and validator documents what it proves, and what it does not, in its
module docstring. What a decoded carrier proves about Story stays in
[`game_data/story_carriers.md`](game_data/story_carriers.md); what it means for
published Story stays in [`webui/story_recovery.md`](webui/story_recovery.md).

## Asset and spatial semantics

AssetMap rows, PPtrs, prefab/component dependencies, material slots, textures,
controllers, clips, effects, and scene records form an evidence chain. A later
link keeps the earlier physical identity and is never replaced by a
normalized-name match.

World registries, LevelData, streaming matrices, NPC proxies, authored pins,
and trigger geometry use separate identity domains. Script-wide context and
proximity never fan out to sibling slots. Dynamic getters and runtime lists are
non-spatial unless a pinned producer proves one immutable authored target.

Semantic asset ownership belongs in
[`game_data/unity_assets.md`](game_data/unity_assets.md); Map publication
belongs in [`webui/map.md`](webui/map.md).

## Source graph

The canonical database is `reports/source_graph/endfield_source_graph.sqlite`.
It indexes evidence already produced by owning builders: a query and
provenance surface, never an authority that invents recovery logic.

```bat
python tools\endfield_source_graph.py query IDENTIFIER
python tools\endfield_source_graph.py story STORY_KEY --limit-lines 8
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Default builds keep only the exact AssetMap rows consumed by WebUI material,
shader, texture and FMV edges; full builds are for exhaustive PathID work.
Every edge keeps an evidence kind; availability, registration, address order
and mission context never become ownership or chronology. Before deleting or
renaming a generated report, search graph readers and rebuild the database if
that report is an input.

## Diagnostics

Use the closest owning report first: `reports/export/`, `reports/animestudio/`,
`reports/game_data/`, `reports/assets/`, `reports/audio/`,
`reports/source_graph/`, `reports/story/build/`, `reports/story/recovery/`.
Revisitable probes belong in `scratch/<topic>/`; disposable intermediates in
`tmp/<topic>/`.

## Recovery queue

In priority order. Offline work first; request a live capture only for a
residual that cannot be resolved offline.

1. **LevelScript batch.** The newly gated `0x00C9` FacGetBuildingPosition,
   `0x0479` SettlementUpgradeShow, GetterBase `0x001C`
   CheckPerformanceReady, `0x00AE` EnvironmentEnable, and ActionHeader
   `0x00DF` OnSettlementReadyPerformance form one recovered chain. A
   hash-checked replay of only the 18 files named by the final contract
   reaches `complete:named_exact` in all 18; whole-owner closure still awaits
   one combined JsonData gate at the publication boundary. ActionHeader
   `0x006A` LevelEvent_OnEntityHpChanged yields four named exact frames and
   eight later ActionHeader stops in its selected cohort. The newly gated
   `0x0007` AddBuffsToTargetSelves advances its 11 selected files to
   ActionBase `0x0475` SetSquadSpecialIdleEnable (nine), `0x0405`
   SetEnemyUIShowRange (one), and `0x0446` SetListBuff (one). The gated
   `0x0405` replay moves its single selected file to ActionBase `0x0111`.
   The gated
   `0x0475` route then advances its nine selected files to PureGetter
   `0x03B4` ListMakeEntityPtr (five), `0x018A` GetterLevelScriptPtr (two),
   and `0x0182` GetterEntityPtr (two). The gated `0x03B4` route advances
   its five files to `0x0182`, making seven selected files there. The gated
   `0x0182` route advances all seven to `0x018A`, making nine selected
   GetterLevelScriptPtr files. The gated `0x018A` replay advances four
   of these to ActionHeader `0x009C`, three to ActionHeader `0x00A4`,
   one to GetterBase `0x0030`, and one to ActionHeader `0x0045`.
   The gated `0x0030` EntityToString replay moves its one file to
   `0x00A4`. The gated `0x009C` OnSpawnerStart replay moves three files
   to ActionHeader `0x0031` and one to `0x00A4`, bringing the latter
   selected cohort to five. The gated `0x0446` SetListBuff replay moves
   its one file to GetterBase `0x018E`. IsLookAtPointInScreen `0x0111`
   advances its one selected file to ActionBase `0x0374`. GetterListBuff
   `0x018E` advances its one selected file to named-exact EOF; whole-owner
   closure still awaits the combined gate. The gated `0x00A4`
   OnSpellAbnormalStart replay advances all five selected files to
   ActionHeader `0x009E`, while `0x0374` PlayVoiceNarrative advances its
   one file to ActionBase `0x03BA`. The gated `0x0031`
   OnPhysicalNoGuard replay moves all three selected files to ActionHeader
   `0x0030` (21 members), distinct from GetterBase `0x0030`. The gated
   `0x0045` OnAnyEntityDie replay advances its one file to ActionHeader
   `0x0043`, and the gated `0x009E` OnSpawnerWaveBegin replay advances
   all five selected files to ActionHeader `0x00BA`. The gated `0x03BA`
   ScriptedCharTeleportTo replay advances its one selected file to
   ActionBase `0x03B5`.
   The gated `0x0030` OnPhysicalInfliction replay advances all three
   selected files to ActionHeader `0x00BA`; the gated `0x0043`
   OnAnyEnemyPoiseZero replay advances its one file to ActionHeader
   `0x0042`.
   The gated `0x03B5` ScriptedCharPatrolStart replay advances its one
   selected file to ActionBase `0x04BF`.
   The gated `0x00BA` OnBBVariableChanged replay reaches named-exact EOF
   in all eight selected files; whole-owner closure awaits the combined
   JsonData gate.
   The gated `0x0042` OnAnyEnemyPoiseKnotBreak replay reaches named-exact
   EOF in its one selected file; whole-owner closure awaits the combined
   gate.
   The gated `0x0040` OnAetherEnergyLockEndPointScanned replay reaches
   named-exact EOF in its two selected files, pending the combined gate.
   The gated `0x04BF` StopCharScriptedMode replay advances its one
   selected file to GetterBase `0x004E` (eight members).
   The gated `0x0053` OnCutsceneExit replay reaches named-exact EOF in one
   selected file and advances the other to ActionHeader `0x004E` (15
   members), distinct from GetterBase `0x004E`.
   The gated PureGetter `0x0053` GetCurSquadAllDead replay reaches
   named-exact EOF in all six selected files; runtime squad state and
   whole-owner closure remain unobserved.
   The gated GetterBase `0x004E` GetCharacterTemplateId replay advances
   its one selected file to ActionHeader `0x00CD` (18 members).
   The gated `0x000F` OnEntityDie replay reaches named-exact EOF in all three
   selected files after the native-gated enemy enum and nullable-float fix;
   the source's undeclared enum value remains numeric.
   The gated ActionHeader `0x004E` OnBlightMiasmaWeakGuide replay reaches
   named-exact EOF in its one selected file.
   The gated `0x00CD` OnStartScriptControlledCharMode replay reaches
   named-exact EOF in its one selected file.
   The gated `0x009B` OnSpawnerPause replay reaches named-exact EOF in
   its three selected files.
   The gated `0x0032` BuildingPosHintShow replay advances nine selected
   files to ActionBase `0x0031` (eight) or `0x00CA` (one), both still unknown.
   The gated GetterBase `0x03E3` NpcGetPackAnimHasClean replay advances
   seven selected files to ActionHeader `0x007C`.
   The gated `0x005C` OnEncounterIntroPartEnd replay reaches named-exact EOF
   in its one selected file.
   The gated ActionBase `0x0031` BuildingPosHintHide replay closes six of
   eight selected files and advances the other two to ActionBase `0x00CA`
   and GetterBase `0x0144`.
   The gated ActionHeader `0x007C` OnNpcDirtyBlockCleaned replay reaches
   named-exact EOF in all seven selected files.
   The gated ActionBase `0x00CA` FacGuideHintEnable replay reaches
   named-exact EOF in both newly exposed selected files.
   The gated ActionHeader `0x008B` OnServerDialogExit replay reaches
   named-exact EOF in seven of eight selected files and advances the eighth
   to ActionHeader `0x0077`, which then reaches named-exact EOF in that one
   file. The gated GetterBase `0x0144`
   GetScriptTaskObjectiveIsCompleted replay advances its one source to the
   `taskMap.entries` CheckIsInFacLinkingMode condition. Its separately gated
   native reader and one-source replay now close every task entry and
   triggerVolumes at named-exact physical EOF; live objective completion and
   facility linking remain unobserved.
   The gated ActionBase `0x03FC` SetDecorationAnimatorInt replay closes three
   of eight selected files and advances five to ActionBase `0x0077`, `0x04AE`,
   or `0x04A1`. The gated ActionBase `0x04C2` StopEffectOnNpcProxy replay
   closes seven of eight and advances one to GetterBase `0x01C5`.
   The gated ActionBase `0x0343` NpcStopCurMontage replay advances all eight
   selected files to ActionBase `0x04D6`.
   The gated ActionBase `0x045E` SetMainCharHpBarActive replay advances its
   seven selected files to ActionHeader `0x00E4` (three) and ActionBase
   `0x0521` (one), `0x0472` (two), or `0x04EC` (one). The gated ActionBase
   `0x0077` DestroyAbilityEntity replay advances its three selected files to
   ActionHeader `0x00A1`; this is separate from ActionHeader `0x0077`.
   The gated ActionHeader `0x00A1` OnSpecificEntityDie replay then reaches
   named-exact EOF in all three selected files.
   The gated GetterBase `0x01C5` IsEndminGender replay reaches named-exact EOF
   in its one selected file after correcting the Gender enum labels to native
   values 1 and 2.
   The gated ActionBase `0x04D6` TeleportGameplayNpc replay advances all eight
   selected files to ActionHeader `0x007D` (21 members).
   The gated ActionBase `0x0521` ApplyMovementSettingModifier replay advances
   its one selected file to ActionHeader `0x00E4` (16 members). The gated
   ActionBase `0x0472` SetSquadIconActive replay advances its two selected
   files to ActionHeader `0x0098` (18 members) and ActionBase `0x03FD`
   (13 members).
   The gated ActionHeader `0x00E4` OnSubGameStart replay reaches named-exact EOF
   in all four selected files. The gated ActionHeader `0x007D`
   OnNpcPatrolCheckpointReach replay reaches named-exact EOF in all eight
   selected files.
   The gated ActionBase `0x04A1` SkipEntityDieDisplay replay advances its one
   selected file to ActionBase `0x04B3` (16 members).
   The gated ActionHeader `0x0098` OnSpawnerGroupComplete replay reaches
   named-exact EOF in its one newly exposed selected file. The gated
   ActionBase `0x03FD` SetDecorationViewState replay advances the other
   SetSquadIconActive file to ActionBase `0x007E` (9 members).
   The gated ActionBase `0x04EC` ToggleUI_DevOnly replay reaches named-exact
   EOF in its one newly exposed file; the stored HUD flag and key are authored
   inputs, not an observed UI change.
   The gated ActionBase `0x04AE` StartCutsceneAndHideSceneObjectAction replay
   advances its one selected file, including two authenticated stored spans,
   to ActionBase `0x04AD` (19 members). The cutscene keys and entity pointers
   remain authored inputs rather than observed playback or scene visibility.
   The gated ActionBase `0x04AD` StartCutsceneAndControlSceneObjectAction
   replay reaches named-exact EOF in that same selected file after three
   authenticated spans. Its cutscene and target keys remain authored inputs.
   The gated ActionBase `0x04B3` StartFmvAndTeleportAction replay advances its
   one selected file to GetterBase `0x0043` (8 members); its FMV key and
   teleport coordinates remain authored inputs. The gated GetterBase `0x0043`
   FloatGetterIntToFloat replay advances that file to a positive two-element
   `introPart.operaSegments` list. The gated nested reader now consumes both
   records and reaches named-exact EOF in this selected file. Its integer
   input is a stored local getter reference; conversion and encounter
   execution remain unobserved.
   The gated ActionBase `0x007E`
   DisableHudFade replay advances its one selected file to GetterBase `0x000C`
   (8 members), with only a stored true HUD flag established.
   The gated GetterBase `0x000C` BoolGetterMultOr replay reaches named-exact
   EOF in that selected file after six stored local boolean references; no
   runtime boolean result is observed.
   The gated ActionBase `0x00A0` EntityMoveToWithSpeed route joins 63 exact
   spans in seven historical first-stop files. Its selected replay reaches
   named-exact EOF in four, then exposes GetterBase `0x0046` in two and
   ActionBase `0x0316` in one. Gated `0x0046` FloatGetterPlus joins 26 exact
   spans and closes its two selected files at named-exact EOF. Gated `0x0316`
   MoveBambooLast proves a stored entity parameter in the remaining selected
   file and advances it to ActionBase `0x03E8`. Gated `0x03E8`
   SetBambooPosIndex then proves a positive two-entity list and constant
   index in that same file, advancing it to ActionHeader `0x00A2`. Gated
   `0x00A2` OnSpecificEntityListDie proves a positive three-entity filter
   and local output path, then closes that selected file at named-exact EOF.
   Stored movement, getter, Bamboo position and event inputs do not establish
   runtime results; whole-owner closure awaits the combined gate.
   A separate gated StopRadio `0x04C7` cohort joins seven historical first
   stops with authored radio IDs. Selected replay closes five files and
   exposes ActionHeader `0x00B6` and GetterBase `0x009F` in one file each.
   Gated `0x00B6` OnClientGlobalVarChanged closes its one selected file at
   named-exact EOF after a stored mission-variable key and local long output
   paths. Gated GetterBase `0x009F` GetInteractivePropertyInt closes the other
   selected file at named-exact EOF after stored entity and string-key inputs.
   The seven-file StopRadio cohort is now source-scoped closed. Radio IDs,
   mission-variable inputs and the property key do not establish live effects
   or a runtime getter result.
   A separate seven-file historical GetterBase `0x013C` cohort now passes a
   gated GetMissionSavePropertyInt reader and reaches named-exact EOF in every
   selected file. The stored mission ID and path do not establish the runtime
   property value. Whole-owner closure still awaits a combined gate.
   A separate seven-file historical ActionBase `0x04B7` cohort now passes
   gated StartNarrativeBlackScreenAndTeleport storage, including one positive
   LangKey text list per selected file. Five reach named-exact EOF. Gated
   SetSquadEnableRelaxIdle `0x0471` advances its newly exposed file to
   ActionBase `0x0042`; gated OnScriptPreStart ActionHeader `0x00C9` closes
   its one newly exposed file at named-exact EOF. Gated CharacterPlayMontage
   `0x0042` then closes the last selected file at named-exact EOF. All seven
   selected files close; whole-owner closure awaits a combined gate. Stored
   inputs do not establish live playback, black-screen display, teleport,
   idle change, or event execution.
2. **BuffData.** The gradual positive-damage branch now has a reviewed native
   contract and reader, and its selected source closes all 30 root fields at
   physical EOF. A separate selected positive-heal root now also closes all
   30 fields at physical EOF through its `CheckHealTag` condition and tag-zero
   processor. A separate tag-`0x21` BreakPassingSmallSceneObject
   `buffEventAction` source also closes one map, sequence, action and all 30
   root fields at physical EOF. The selected `buff_equipsuit_defup_01` root
   closes its positive attribute child and its empty-condition tag-ten damage
   child before reaching all 30 fields at EOF. These local audits are scoped
   to their sources; the whole BuffData catalog is unchanged pending a
   combined gate. The remaining sword root needs several new nested grammars;
   other positive `damageModifier` children and positive
   `attributeModifier` sources,
   anonymous event-action interiors and positive finder bodies need their own child
   proofs.
3. **SkillData.** The 26 reviewed cursor targets and one positive control
   have exact current source/native closure under a bounded 27-file sparse
   report; this does not classify unstreamed SkillData. Probe only historical
   unknown rows against the existing receipts. Three Mifu rows were streamed
   once: two close under the shared parser, and combo reaches whole stored
   schema only in an isolated native-validated `0x004B` CheckSkillHasHit
   diagnostic. Five Zhuangfy routes are now in the shared parser. The newly
   checked Lizhiyan combo source has a selected static terminal after its
   ActionGroup, but no whole-schema or family publication. The selected
   Pograni ultimate source also reaches structural EOF after admitting its
   `0x0152` route. Its newly checked VFS bytes match the selected copy, but
   the shared parser still stops at that route and no live terminal cursor
   names the final fields. One reviewed two-source capture contract and host
   preflight now cover Lizhiyan and Pograni together without rechecking the
   unchanged Lizhiyan chunk.
   Rebind unchanged
   corpus rows with current parser provenance or run the normal family gate
   once; do not restream already closed Zhuangfy sources merely to refresh
   diagnostics. Rank remaining distinct action stops after that boundary.
4. **Gameplay formulas.** Selected damage/Poise evaluators and callers are
   proven statically ([`game_data/gameplay_semantics.md`](game_data/gameplay_semantics.md));
   receiver identity, live invocation, subtype selection, patch state,
   provider values and final damage remain unresolved.
5. **World.** Streaming needs independent record-end evidence or a bounded
   runtime carrier witness before field names; keep selector9, Marker13 gap
   profiles and Marker17 bodies anonymous; slot-7 field 0 is each group's
   descriptor-ID mask, so its bits stay as anonymous as the IDs. Framing lives
   in `scripts/game_data/streaming/framing.py`; see
   [`game_data/world_chunk_slots.md`](game_data/world_chunk_slots.md) and
   [`game_data/world_chunk_unread_region.md`](game_data/world_chunk_unread_region.md).
   Then Terrain channel meaning and live file selection, DynamicStreaming
   nested main records, auxiliary fields beyond descriptor 21 and live
   grid/area selection, and irradiance root/provider/record semantics.
6. **Audio.** HIRC layout and the shipped decision-tree walk are closed against
   the Wwise SDK and bank corpus; value naming, remaining plug-in blocks, a
   host for layers 5 and 6, and the playback call chains stay in
   [`game_data/audio_overview.md`](game_data/audio_overview.md).
   `scripts/webui/audio/semantics/native_callsite_rederivation.py` re-proves
   the native catalog by name on a new build.
7. **Catalog and code.** BundleManifest cross-store identity and live lookup,
   mmap, and IFix patch execution.
8. Improve exact prefab, renderer, material, animation and world-instance
   ownership, and keep native gates and graph provenance deterministic across
   client updates. LevelScript, LevelData, Spawner, Story and the Buff action
   dispatcher resolve union tags by name; literal AbilityActionData tags remain
   in `skill_timeline_shared_sequence`, `buff_residual_actions`, the nested
   selector/processor profiles of `buff_actions`, `buff_corpus` frontier lists,
   receipt `TAG` constants and `buff.py` tables. Their per-route native
   contracts still refuse another build, but convert them before the next
   client update.
