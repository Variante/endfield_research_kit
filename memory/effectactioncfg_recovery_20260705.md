# EffectActionCfg Projectile Effect-List Recovery - 2026-07-05

## Result

AnimeStudio now decodes the last raw `Beyond.Gameplay.EffectActionCfg` byte
region in the focused template families: the projectile effect-list prefix
inside the `ProjectileComponentData` tail
(`effectListAndFinishPrefixRawWords`).

The decoder is byte-guarded:

- the region (bounded end-relative by the already-proven
  `showAlertEffect + alertEffect + 9-word sound tail` suffix) must consume
  exactly as `mainEffects`, `launchEffects`, `showReachEffectOnlyWithTarget`,
  `reachEffects`, `hitEffects`, `blockEffects`,
  `showFinishEffectOnlyWhenUnblockAndNotHit`, `finishEffects`;
- each list is `int32 count` (guarded 0..64) of EffectActionCfg entries;
- each entry is a strict `fxType` enum (Normal/Alert/BottomScreen/WeaponVfx
  values only), an aligned ASCII `effectName`, the proven 24-word post-name
  prefix omitting `useScaleBB`, and the proven 80-word EffectActionCfg tail
  (`ReadProjectileAlertEffectActionCfgTail`, relabeled
  `EffectActionCfg/ProjectileEffectListTail`);
- `TryReadProjectileAlertEffectActionCfgPrefix` gained a
  `requireExactTailRemaining` flag so list entries (which are not
  end-of-region) reuse the same 24-word prefix guard while the alertEffect
  caller keeps its original exact-remaining behavior;
- on any guard mismatch the exporter emits the previous
  `effectListAndFinishPrefixRawWords` diagnostic unchanged
  (`effectListAndFinishPrefixStatus = "rawFallback"`).

## Evidence

A stdlib-only mirror parser
(`scratch/effectactioncfg_20260705/parse_effect_lists.py`) replayed the raw
prefix words preserved in the 2026-07-03 focused validation outputs
(`tmp/projectile_movemode_variable_after_20260703`,
`tmp/projectile_movemode_variable_persistent_after_20260703`).

- omit-`useScaleBB` body (alert-style, 104 post-name words):
  **310/310 regions consume exactly**, 0 BlackboardDouble raw fallbacks,
  536 entries, every entry body exactly 104 words, all `fxType = 0` (Normal),
  all inner strings empty, all `effectPosData` arrays empty.
- with-`useScaleBB` body (deadEffect 107-word style): fails 288/310 with
  bool-guard violations; the 22 "passes" are all-empty regions that never
  exercise the entry shape. This variant is disproven for list entries.

The IL2CPP metadata field order for `ProjectileComponentData`
(`mainEffects` .. `finishEffects` between `mainEffectFinishDistance` and
`showAlertEffect`) matches the byte order exactly.

## Validation

`.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore` passed
(0 errors). Focused before/after exports at the same asset selections into
`tmp/effectactioncfg_before_20260705` (pre-change binary, HEAD `7240b1f`) and
`tmp/effectactioncfg_after_20260705`, using
`tmp/projectile_curve_filter_20260703.json`,
`tmp/projectile_component_all_20260630/source_01.filter_data.json`, and new
asset-map filters `tmp/effectactioncfg_filter_{eny,chr,abilityentity}_{streaming,persistent}_20260705.json`.

```text
projectile_streaming  (300 files): 300 prefix regions decoded, 0 rawFallback
                                   524 entries; lists: 1285 empty / 506 x1 / 9 x2
projectile_persistent (10 files):  10 decoded, 0 rawFallback, 12 entries
eny_streaming        (78 files):   byte-identical before/after
eny_persistent       (78 files):   byte-identical (incl. the single
                                   EffectActionCfg/OmitUseScaleBBTail user of the
                                   shared prefix helper)
chr_streaming        (28 files):   byte-identical
chr_persistent       (2 files):    byte-identical
abilityentity_streaming (160):     byte-identical
abilityentity_persistent (1):      byte-identical
no $unparsed / $heuristic markers anywhere in before or after
```

Cross-check: the C# after-export decodes the same 536 entries with the same
fxType/name/list-count distributions as the Python mirror (e.g. top name
`P_fxbat_tangtang_attack_01_hit_01` x13; entry serialized word counts 111-119,
always `2 + nameWords + 104`).

## Remaining Frontier

- No raw EffectActionCfg byte regions remain in the focused projectile /
  enemy / character / ability-entity template families. The remaining
  `EffectActionCfg` nodes are structurally decoded but stay `$partial` for
  semantic reasons only (BlackboardDouble internals as diagnostic wrappers,
  enum value names, `useScaleBB`/`centerOffset` omission proven per-context
  rather than from serializer code).
- Only the empty-inner-string 104-word entry body is byte-proven; entries with
  non-empty `limitKey`/`weaponVfxKey`/blackboard keys or non-empty
  `effectPosData` would consume more than 24+80 words and intentionally fall
  back to raw words until such samples exist.
- `reports/monobehaviour_frontier_tail_audit.*` was NOT refreshed: its inputs
  (`reports/monobehaviour_frontier_latest.json` from the decoded index and the
  `export_full` JSON snapshot) still reflect the pre-2026-07-03 full export, so
  re-running it now would reproduce the stale ranking unchanged. It should be
  refreshed after the next full MonoBehaviour JSON re-export, which will also
  fold in the 2026-07-03 projectile move-mode and ability-entity root passes.
- Next blocker by the stale audit ranking: the large
  `Beyond.Gameplay.AbilityEntityTemplateData` partial payload (gameplay tags,
  skill/model/nav/physical/interactive sections) and `MoveModeData`
  speed-info/enum semantics.
