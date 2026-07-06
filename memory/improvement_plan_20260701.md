# Improvement Plan 閳?2026-07-01

Derived from `memory/original_game_data_understanding_report_20260701.md`, the
current AnimeStudio fork review, and the latest export logs. Ordered by
leverage for recovering more of the original game data. Update status lines in
place as work lands; keep evidence in `reports/`/`tmp/` and conclusions here or
in dedicated memory notes.

## Priority queue

### P1. Project C: IL2CPP gameplay-writer simulation (runtime semantics)
- Goal: recover writer-side runtime evidence past the static ceiling 閳?scene
  playback order for boss/phase clusters (e0m0 q11) and the
  `DialogOptionPlayableAsset` `+0x18` active-clip gate for option-route proof.
- Workspace: `scratch/il2cpp_gameplay_sim/` (Stage 0 done, CodeRegistration
  `0x18C439740`, reusable bridge without capstone).
- Success: at least one boss-cluster playback order and one option-route gate
  value reproduced from simulated writer-side execution.
- Status: in progress (staged); largest effort, do not block other items on it.

### P2. BuffData/SkillData multi-action boundary recovery (action semantics)
- Goal: split timeline `actionData` payloads with `actionDataCount > 1` into
  per-item records, fail-closed, via `IfElseAction` nested action-list
  structure and strict full-chain typed consumption; never header-only splits.
- Where: `scripts/build_data_index.py` (`decode_buff_memorypack` and helpers).
- Baseline (both roots): 338 timeline records, 263 single-item summaries
  exposed; item statuses 11 exact / 141 partial / 111 opaque; 143 BuffData
  rows with unresolved `di` issue fields.
- Success: opaque single-item summaries drop; some multi-action records become
  bounded item lists; row-level warnings never suppressed without proof.
- Status: landed 2026-07-01. Strict full-chain typed consumption plus a
  recursive IfElseAction decoder split 11 of 68 multi-action records into
  typed item lists (`typed-chain-items`); item statuses moved from
  11 exact / 141 partial / 111 opaque to 17 / 171 / 109; typed decoder
  failures stayed 0 and all 143 `di` rows are byte-identical. Remaining
  ceiling is FindTargetAction/SelectorData structure (blocks 20 chains),
  CheckBuffStackNumAdvanced buffSettings tag-queries, DamageAction DamageUnit
  (32 members; also blocks 12 TickInterval singles), and six unknown nested
  union tags. See `memory/animestudio_warning_error_status_20260630.md`
  section "2026-07-01 BuffData Multi-Action Boundary Recovery".
  Reviewed 2026-07-02: approve-with-nits; follow-up landed locally. The
  best-effort probe marker was renamed so it no longer enters `ds`/`di`,
  `decode_buff_effect_action` was unified onto its consume_ twin, and a
  conservative exact-boundary DamageAction probe was added without registering
  DamageAction for multi-action chain consumption. Full Json validation stayed
  warning-preserving (0 changed BuffData `di` rows). A read-only DamageAction
  target-tail audit is complete in `tmp/damage_action_target_tail_audit_20260702.*`:
  five character chains are ambiguous; one enemy chain reaches CameraImpulse.
  Follow-up landed locally 2026-07-02: deterministic CameraImpulse parsing now
  uses member-count 18 plus curve/noise string length to compute the
  TargetSettings boundary, is registered for strict chain consumption, and
  recovers the curve/noise asset candidate. A conservative exact-only
  FindTargetAction partial decoder exposes already-bounded selector bodies
  without enabling chain consumption. DamageAction exact single-item probing is retained, but 2026-07-02 review found DamageAction unsafe for multi-action chain consumption while DamageUnit boundaries remain opaque; it was removed from `BUFF_ABILITY_ACTION_CONSUME_DECODERS`. Bounded common-prefix reads now protect all action consumers, and prefix-only FindTargetAction partials are rejected. Full Json validation after the safety rollback changed only compact `ds` details for the duplicate `buff_eny_0113_jzogre_skill05_onground_attack` rows; file count and `di` warnings stayed unchanged. Direct BuffData scan after the rollback and exact-only FindTarget tail promotion: 24 `typed-chain-items`, 526 `single-item`, 112 ambiguous, 14 empty; item statuses 34 exact / 374 partial / 190 opaque. The FindTarget promotion decodes direction member count/type plus tail target fields for the 20 already-bounded exact partials, but does not enable chain consumption. Next P2 unlocks require new structural evidence: SelectorData end recovery for FindTargetAction, full DamageUnit / HitSoundData / effect/cost subblock recovery, or AnimeStudio raw sidecar boundaries that can be consumed fail-closed.

### P3. Rebuild decoded MonoBehaviour index with current exporter
- Goal: replace the stale 3,644-file incomplete inventory; bucket any
  remaining `references:ManagedReferencesRegistry` failures by the new
  `managedReferencesRegistryRecoveryFailure.reason` diagnostics.
- Where: broad `json_by_type` export + `scripts/build_decoded_index.py`-style
  scan to a fresh index; long-running, schedule deliberately.
- Success: current (not historical) incomplete counts per class family.
- Status: landed 2026-07-05. Full story-scope re-export (maps + json_by_type,
  both roots, current CLI with all 2026-07-03 decoder passes plus the
  2026-07-05 projectile EffectActionCfg effect-list recovery) completed with 0
  command failures; decoded index rebuilt at `webui/data/decoded`
  (1,064,294 MonoBehaviour files, 1,478 groups); frontier report and tail
  audit refreshed. Current truth: 1,063,575 decoded / 719 partial (99.93%),
  residual schemas ProjectileTemplateData 310, AbilityEntityTemplateData 162,
  EnemyTemplateData 156, LineFollower 48, CharacterTemplateData 30, plus 15
  small camera/dialog/remote-factory files. Console partial-MonoBehaviour
  warnings are genuinely zero since 2026-06-29 (11,948 → 221 → 0 as the
  managed-reference and animator-dependency fixes landed); partiality now
  lives in in-JSON `$partial` diagnostics, which is what the index measures.
  Caveat: the tail audit's per-layout "problem refs" counts rose for
  EffectActionCfg (961 → 1,497) because newly decoded effect-list entries
  carry honest semantic-only `$partial` markers; read file-level counts for
  progress and layout counts for target selection. See
  `memory/monobehaviour_index_rebuild_20260705.md`. Next structural targets:
  `AbilityEntityTemplateData` root payload sections (162 files, 49 metadata
  fields, 2 mapped bodies) and `SelectorData`/`TargetSettings` (74 refs in
  CharacterTemplateData; same blocker gating BuffData FindTargetAction chain
  consumption in P2).

### P4. Per-AB clean/dirty status manifests beyond Texture2D
- Goal: extend the `asset_status/convert_by_type_Texture2D.json` manifest
  pattern to all convert/json stages so the 518,131-AB population splits into
  exact clean / partial / conversion-error / not-loaded buckets.
- Where: `tools/AnimeStudio` CLI stages + wrapper summary.
- Success: a report can count certified-clean ABs exactly.
- Status: pending.

### P5. FlatBuffer streaming `.bytes` schema recovery
- Goal: move the 38,561 FlatBuffer-like world-streaming `.bytes` from
  "identified" to clustered root-table shapes with a bounded prototype parser.
- Where: exploration in `scratch/`; promote only stable detectors.
- Success: shape clusters with counts, at least one family parsed exactly or
  bounded with named offsets; a durable memory note of layout findings.
- Status: landed 2026-07-01 閳?38,561/38,824 valid in exactly 5 root-signature
  clusters; chunk-manifest root bounded with named offsets and two exact
  population-scale checks (slot0==46 in 38,064/38,064; slot1 == filename
  coords x128 in 36,554/36,554). See
  `memory/flatbuffer_bytes_schema_recovery_20260701.md` and
  `tmp/flatbuffer_bytes_clusters_20260701.md`. Next: IL2CPP FlatBuffers
  accessor-name recovery before promoting semantic field names.
  Reviewed 2026-07-02: approve-with-nits; probe_vector fix landed the
  same day and the deep dive was re-run (slots 3/4 relabeled
  vector-unproven; 14 shadowed child tables + 3 new signatures found;
  proven slots 2/5/6/7 unchanged). See the 2026-07-02 section of
  `memory/flatbuffer_bytes_schema_recovery_20260701.md`. Next: IL2CPP
  FlatBuffers accessor-name recovery.

### P6. ModelTable -> renderable asset_entity binding via prefab evidence
- Goal: close the 0-match join between 1,201 decoded `model_config_model`
  rows and 10,424 renderable entities using GameObject/Component prefab
  traversal in recovered MonoBehaviour/asset maps, not filename matching.
- Success: nonzero `model_config_asset_entity` edges with source evidence;
  `int_doodad_ore_cluster_*` family resolves to renderable owners.
- Status: in progress. Current source-graph follow-up report now classifies
  1,280 decoded model config rows against 10,678 asset entities, with 215
  direct `model_config_asset_entity` edges, 200 strong exact rows, 10
  ambiguous rows, and 10 name-only candidate rows. The original 0-match audit
  is stale as a baseline but still documents why naive matching was
  insufficient. Remaining gap is the 161 referenced rows with no exported
  renderable candidate, including
  `int_doodad_ore_cluster_*`; use
  `python tools\endfield_source_graph.py model-bindings --status no_exported_renderable_candidate`
  to inspect them.

### P7. Formula recovery pilot (2-3 systems)
- Goal: map table columns to IL2CPP getter/evaluator methods for character
  growth, weapon ATK, and one damage path; one fully proven formula chain.
- Status: in progress. Character growth and attribute/stat table evidence is
  already queryable, and 2026-07-06 source graph work adds authored weapon ATK
  level checkpoints from `WeaponUpgradeTemplateTable.list[]`: 1,890 normal
  upgrade rows now link to `gameplay_stat_property:atk`, with matching
  checkpoint nodes for the cumulative upgrade-sum rows. This improves the
  weapon ATK pilot slice while still stopping short of IL2CPP evaluator proof
  or runtime formula execution. See
  `memory/weapon_atk_checkpoint_source_graph_recovery_20260706.md`.

### P8. Cleanup queue (cheap, background)
- Classify 110 unbound FMV-scope videos and 18 unresolved narrative refs.
- Ingest decoded managed-reference `soundName`s into the audio catalog.
- Keep the 35-scene story gap hotlist shrinking with tagged evidence only.
- Status: in progress. Decoded managed-reference `soundName` / audio event
  refs are now source-graph audio links with reverse lookup from audio nodes;
  see `memory/monobehaviour_soundname_audio_source_graph_recovery_20260706.md`.
  Unresolved narrative-video candidates now have a generated source-graph
  follow-up report that separates 3 `hasGeneratedStoryTarget` groups from 4
  `noGeneratedStoryTarget` groups; see
  `memory/unresolved_narrative_video_followup_report_20260706.md`.
  Remaining cleanup is to classify or bind the 110 unbound FMV-scope variants,
  decide the 3 actionable narrative-video groups, and continue shrinking the
  story-gap hotlist with tagged evidence only.

## Ground rules for all items

- Fail-closed decoding: promote parsers only when bytes consume exactly or
  tails stay named/bounded; keep `$partial`/`di` warnings visible.
- Static evidence and observed-runtime order remain separate evidence classes.
- Python stays stdlib-only; one-off exploration starts in `scratch/`/`tmp/`;
  durable conclusions land in `memory/`.
