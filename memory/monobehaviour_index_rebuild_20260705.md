# MonoBehaviour Index Rebuild - 2026-07-05

## Result

Improvement-plan P3 landed: the decoded MonoBehaviour inventory is now current
instead of historical. Pipeline, in order:

1. Full story-scope re-export with the current AnimeStudio CLI (all
   2026-07-03 decoder passes plus the 2026-07-05 projectile EffectActionCfg
   effect-list recovery in the working tree):
   `python scripts\export_full_from_game.py --animestudio-stages maps
   json_by_type --animestudio-scope story --animestudio-dummy-dlls
   tools\DummyDll --skip-structured --skip-vfs-index`
   Run report: `reports/20260705_110457/`. 4 commands, 0 failures, 0 failed
   entries; StreamingAssets json=1,109,797, Persistent json=105,266 (same
   populations as the 2026-07-03 run).
2. `python scripts\build_decoded_index.py` → `webui/data/decoded`
   (1,064,294 MonoBehaviour files, 10,978.5 MiB, 1,478 groups).
3. `python scripts\build_monobehaviour_frontier_report.py` →
   `reports/monobehaviour_frontier_latest.*`
4. `python scripts\story_recovery\build_monobehaviour_frontier_tail_audit.py`
   → `reports/monobehaviour_frontier_tail_audit.*`

## Current frontier truth

- `decoded`: 1,063,575 files; `partial`: 719 files across 15 groups (99.93%).
- Residual schemas: ProjectileTemplateData 310, AbilityEntityTemplateData 162,
  EnemyTemplateData 156, LineFollower 48, CharacterTemplateData 30,
  CameraControl*Config 7, RemoteFactoryEntityTemplateData 3,
  DialogMainFlowData 3.
- Residual domains: camera/cinematic 479, gameplay/ability 186,
  managed-reference 51, story/dialog 3.
- No raw-word EffectActionCfg regions remain anywhere in the focused
  families; remaining `$partial` markers on EffectActionCfg nodes are
  semantic-only (enum value names, BlackboardDouble diagnostic wrappers,
  per-context useScaleBB/centerOffset omission proven by bytes rather than
  serializer code).

## Two measurement caveats (do not misread later)

- Console `Partially decoded MonoBehaviour` warnings are genuinely zero since
  the 2026-06-29 evening runs (06-27 baseline 11,948 + 1,486 → 221 on 06-29
  morning, all `BB_npc_*` → 0 after "Load animator export dependencies"
  landed). The empty `*_json_by_type.stdout.log` files since then are real,
  not a log-capture bug. Partiality is recorded in-JSON and measured by the
  decoded index, not by log scraping.
- The tail audit counts `$partial` layout nodes as "problem refs", so
  successful structural recovery can RAISE a type's count when it exposes
  many honest semantic-partial children (EffectActionCfg went 961 → 1,497
  after the effect-list recovery decoded 536 new entries). Use file-level
  residual counts for progress tracking and layout-level counts only for
  picking parser targets.

## Next structural targets (from the refreshed audit)

- `Beyond.Gameplay.AbilityEntityTemplateData` root payload sections
  (162 files; 49 metadata fields; 2 mapped GameAssembly bodies; gameplay
  tags, skill/model/nav/physical/interactive sections).
- `Beyond.Gameplay.Core.Selector/SelectorData` + `TargetSettings`
  (74 refs in CharacterTemplateData groups). This is the same SelectorData
  end-recovery blocker that gates BuffData `FindTargetAction` chain
  consumption (P2), so one proof would pay twice.
- `MoveModeData` speed-info/enum semantics (331 refs, semantic-only).
- Small clusters: LineFollower 48, CameraControl*Config 7,
  DialogMainFlowData 3, InteractiveEvent EnterThrowMode/AttachToInstigator 12.

Related: `memory/effectactioncfg_recovery_20260705.md`,
`memory/abilityentity_root_recovery_20260703.md`,
`memory/improvement_plan_20260701.md` (P3 status),
`memory/toolchain_recovery_push_20260702.md` (SelectorData evidence gates).
