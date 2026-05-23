# Static-data frontier for scene-order recovery

This note records the boundary where the WebUI `build_story_order.py` pipeline
stops being improvable by adding more general rules. Read this before
re-exploring "can we get a smaller mismatch on e0m0 / boss-cluster missions" —
several promising-looking angles have already been tried and confirmed to be
dead ends.

For the general scene-order framework, edges, and chunk model, see
[scene_file_order_recovery.md](scene_file_order_recovery.md).

## e0m0 calibration target

Manual gameplay-observed order:
[e0m0_observed_order_calibration.json](e0m0_observed_order_calibration.json)
under `e0m0.order` (45 entries). This is the archived calibration target, not
an active builder override.

Inversion metric = unordered-pair Kendall-tau against that GT, on the
intersection of recovered and GT keys.

| version | rule added | inversions / 990 | rate |
| --- | --- | ---: | ---: |
| baseline | — | 225 | 22.7% |
| v1 | content-suffix-proximity for orphan conv keys | 140 | 14.1% |
| v2 | cross-level-orphan-chunk-tail | 62 | 6.3% |
| v3 | direct-spatial-quest (per-scene script-float vs quest pins) | 50 | 5.1% |
| v4 | header-chain edge constraints | 50 | 5.1% (no-op today) |
| v5 | start-shape-quest-pin (firm start shape only) | 50 | 5.1% |
| v6 | start-shape-quest-pin extended to triggerVolumes | 51 | 5.2% |

Corpus-wide impact (200 missions, 4670 entries):

- content-suffix-proximity: 1939 firings
- direct-spatial-quest: 813
- start-shape-quest-pin: 234 (up from 14 when restricted to firm start shapes)
- cross-level-orphan-chunk-tail: 26
- header-chain edge: 0 net changes (acts only inside same-bucket ties that
  already follow byte order; left in place as a safeguard for future header
  decode improvements)

## What the remaining ~5% looks like

The remaining e0m0 inversions cluster in two places, both representative of
the static-data wall:

1. **q#11 boss cluster intra-order** in `indie_dg002/8700050001`.
   `cs_3`, `cs_4`, `cs_5`, and `radio_e0m0_13..23` all share one trigger
   volume cluster and one quest anchor (q#11). Their playback order is
   `cs_3 → 13 → 14 → 16 → 22 → 23 → 17 → 15 → cs_4 → 20 → cs_5` per GT,
   which is non-monotone in every static field (localId, byte offset,
   numeric suffix). The boss cluster genuinely requires runtime state to
   decide playback order.
2. **`radio_e0m0_21`** has no LevelScript binding at all. The play-trigger
   audit row 50 records `unknown-start`, `no LevelScript play chain
   recovered`. Either a hash-keyed reference we didn't decode, or it really
   has no LevelScript binding (fired by gameplay code with no LS proxy).

## Static signals that were exhausted

### LevelScript binary structure

- **`battle_field_clear` writer search**: literal string appears in exactly 1
  file globally, as the *read* side (`0x0bed/0x00` terminal-branch at
  `8700040000`). Gameplay runtime sets it; no LevelScript action writes it.
- **`<scene>Played` properties**: 9 distinct keys exist globally, all
  single-file references. Each is a play-once debounce sitting two localIds
  before its play action (`gate_K reads <X>Played → action_K+2 plays X`). No
  cross-script `_Played` references; no ordering signal.
- **`0x0a03/0x00` compact gates**: 219 globally, 125 distinct property keys.
  Property keys are mostly generic state flags (`guide1`, `attackstart`,
  `isFinished`, `in_tower`). The remaining keys are setter-targets the
  audit's setter-overlap pass already proved are written from gameplay code
  rather than from any `Set<T>` MemoryPack record. See
  [scene_file_order_recovery.md](scene_file_order_recovery.md) §
  "2026-05-19 Compact Gate And Setter Overlap Follow-up".
- **`0x104a/0x00` float-property-signal**: each record listens for
  `$<localId>@_floatValue` and fires `nextId`. Recovered chains re-encode
  byte order — no cross-localId jumps. 28 such headers in `8700050001`
  resolve to a sequential chain, not the runtime fire order.
- **`0x12a1/0x00` trigger-enter**: `8700050001` has only 1 such record
  (`localId=180, nextId=0`). The trigger just activates the script; what
  fires inside is determined by gameplay state.
- **Header-chain edges (`ActionHeader.nextId` chains)**: wired into
  `apply_scene_file_order_constraints` as same-bucket tie edges. Across 200
  missions the edges never change the output — chain order is already byte
  order. Kept as a future-proof seam.

### AnimeStudio recovery

- `timeline_line_orders.json` covers `dlg_*` dialog timeline clips only;
  not cutscene or radio sequencing.
- Per-cutscene `.playable` MonoBehaviour exports describe clips *within*
  one cutscene (animation timing, subtitle clips), not ordering *between*
  cutscenes. There is no master Timeline that sequences boss-cluster
  cutscenes.
- Audio event tags carry narrative phase markers in some cutscene names
  (`au_music_cs_tundra_000_boss_intro`, `..._boss_pre_end`,
  `..._pick_stone`). The signal is real but sparse — too few cutscenes carry
  enumerable narrative-phase tokens to extract a general ordinal mapping
  without a curated dictionary, and the rows that do carry tokens are
  already correctly ordered by `direct-spatial-quest`.

### Trigger volume positions

`triggerVolumes` records carry decoded positions even when `startShapeList`
is null. Extending `start-shape-quest-pin` to also consume trigger-volume
positions multiplied firings from 14 to 234 across 73 missions. This is the
last large-scope spatial signal in the LevelScript binary; nothing else of
similar shape is unconsumed.

## Why static rules can't move the needle further

The boss-cluster ordering question can be restated as: *given that one
`OnLeaderEnterTriggerVolume` activates `8700050001`, which `_floatValue`
gets set first, second, third, …?* Those `_floatValue` writes happen in
runtime gameplay code (battle phase counters, boss HP thresholds, "monster
reaper killed N times"), not in the LevelScript binary. The binary contains
**listeners** for those values but not the **writers**. No amount of
LevelScript binary decoding can recover the writer sequence because the
writers don't exist there.

Standard ActionBase setters (`SetBool`, `SetInt`, `SetIntIncrease`) are
fully decoded and **zero** of them match the MissionRuntime property checks
or the `<scene>Played` family. See the setter-overlap audit referenced in
the scene-order recovery file.

## What would actually move it

1. **Manual scene-order overrides.** Use
   [story_order.json](../webui/overrides/story_order.json)
   for specific WebUI final-order fixes. The active format is
   `missions.<mission>.order`: each mission stores one complete ordered list of
   Story file keys. The browser applies this at load time, so edits only need a
   browser refresh. Set `missions.<mission>.locked: true` when a manual list
   should not be refreshed by the builder or OCR recovery.
   For e0m0 the observed order remains a calibration target, not a static
   recovery method; manual overrides should be used only where a user
   explicitly wants the WebUI to prefer observed order over static evidence.
2. **Game-state simulation.** Decompile IL2CPP's battle/quest/property
   modules to recover the writer side. This is a research project of a
   different shape from the static recovery pipeline.
3. **Boss-cluster narrative-phase dictionary.** Enumerate audio tag tokens
   (`*_intro`, `*_pre_end`, `*_climax`, `*_end`, `*_outro`, `*_finale`,
   …) into an ordinal map and tiebreak same-quest cutscenes by that map.
   Would help only the small subset of cutscenes that carry such tokens
   and the gain over the current `direct-spatial-quest` order is marginal.
   Not worth the curation cost unless someone is already maintaining the
   dictionary for another purpose.

## Recommendation for future sessions

If the WebUI's mission-order accuracy needs to improve again:

- **Do not** add another sort-key heuristic to `event_phase`. The
  combination of quest-DAG + per-scene spatial + per-script trigger
  position + content-suffix is already at the static-data ceiling.
- **Do** add `webui/overrides/story_order.json` entries for the specific
  mission being calibrated, and accept the `manual-scene-order` evidence label.
- **Do not** re-attempt the property-setter decode (`0x0a03/0x00` writes,
  `0x104a/0x00` writers, `<scene>Played` writers). The setter-overlap and
  string-search audits already proved the writers are not in the
  LevelScript binary.
- **Do** keep an eye on whether new IL2CPP runtime field exposures from
  GameAssembly (e.g. a new ActionBase formatter tag for `Set<T>` with
  property-key semantics) appear in the
  [levelscript_actionbase_formatter_tags](../reports/mission_order/levelscript_actionbase_formatter_tags.md)
  audit. If a new setter family gets a name, re-run the
  `build_levelscript_setter_overlap_audit.py` and check whether the
  property-check triples become covered.
